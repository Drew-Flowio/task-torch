"""UI-only live transcription tap — parallel capture + periodic whisper partials."""

from __future__ import annotations

import subprocess
import tempfile
import threading
from dataclasses import dataclass

import numpy as np
import sounddevice as sd
import soundfile as sf
from PySide6.QtCore import QObject, QThread, QTimer, Signal


@dataclass(frozen=True)
class SttPaths:
    whisper_cli: str
    whisper_model: str
    threads: int = 4
    sample_rate: int = 16000


class PartialTranscribeWorker(QThread):
    finished_text = Signal(str)

    def __init__(self, wav_path: str, paths: SttPaths) -> None:
        super().__init__()
        self._wav_path = wav_path
        self._paths = paths

    def run(self) -> None:
        try:
            cmd = [
                self._paths.whisper_cli,
                "-m", self._paths.whisper_model,
                "-f", self._wav_path,
                "-l", "en",
                "-t", str(self._paths.threads),
                "-nt",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            text = " ".join(lines).strip()
            if text:
                self.finished_text.emit(text)
        except (subprocess.CalledProcessError, OSError):
            pass


class LiveTranscriptTap(QObject):
    """Captures mic audio for live partial transcription display (UI layer only)."""

    partial_text = Signal(str)
    level_changed = Signal(float)

    PARTIAL_INTERVAL_MS = 1600
    MIN_PARTIAL_SECONDS = 0.6

    def __init__(self, paths: SttPaths, device: int | str | None = None) -> None:
        super().__init__()
        self._paths = paths
        self._device = device
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._active = False
        self._partial_worker: PartialTranscribeWorker | None = None
        self._last_partial = ""

        self._timer = QTimer(self)
        self._timer.setInterval(self.PARTIAL_INTERVAL_MS)
        self._timer.timeout.connect(self._run_partial)

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def paths(self) -> SttPaths:
        return self._paths

    def start(self) -> None:
        if self._active:
            return
        self._frames = []
        self._last_partial = ""
        self._active = True

        def _callback(indata, frame_count, time_info, status):  # noqa: ARG001
            with self._lock:
                if not self._active:
                    return
                self._frames.append(indata.copy())
                energy = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
                self.level_changed.emit(min(1.0, energy / 3000.0))

        try:
            self._stream = sd.InputStream(
                samplerate=self._paths.sample_rate,
                channels=1,
                dtype="int16",
                device=self._device,
                callback=_callback,
            )
            self._stream.start()
            self._timer.start()
        except OSError:
            self._active = False

    def stop(self) -> str | None:
        self._timer.stop()
        self._active = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._frames:
                return None
            audio = np.concatenate(self._frames, axis=0)
            self._frames = []
        if len(audio) < self._paths.sample_rate * 0.2:
            return None
        out_path = tempfile.mktemp(suffix=".wav")
        sf.write(out_path, audio, self._paths.sample_rate, subtype="PCM_16")
        return out_path

    def cancel(self) -> None:
        self._timer.stop()
        self._active = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            self._frames = []
        self._last_partial = ""

    def current_guess(self) -> str:
        return self._last_partial

    def _run_partial(self) -> None:
        if not self._active or self._partial_worker is not None:
            return
        with self._lock:
            if not self._frames:
                return
            audio = np.concatenate(self._frames, axis=0)
        if len(audio) < int(self._paths.sample_rate * self.MIN_PARTIAL_SECONDS):
            return
        tmp = tempfile.mktemp(suffix=".wav")
        sf.write(tmp, audio, self._paths.sample_rate, subtype="PCM_16")
        worker = PartialTranscribeWorker(tmp, self._paths)
        worker.finished_text.connect(self._on_partial)
        worker.finished.connect(lambda: setattr(self, "_partial_worker", None))
        self._partial_worker = worker
        worker.start()

    def _on_partial(self, text: str) -> None:
        if text and text != self._last_partial:
            self._last_partial = text
            self.partial_text.emit(text)
