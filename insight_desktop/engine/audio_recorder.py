"""Microphone capture for the "press to talk" voice flow.

Uses `sounddevice` (PortAudio bindings) so this works unchanged on macOS,
Linux (including a Raspberry Pi with a USB/I2S mic), and Windows — no
platform-specific recording code anywhere else in the app.
"""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf


class AudioRecorder:
    """One recorder instance per app. Not safe to call `start()` again
    while already recording — `engine/interface.py` guards against that
    via the app's Idle/Listening state."""

    def __init__(self, sample_rate: int = 16000, device: int | str | None = None, max_seconds: int = 20):
        self._sample_rate = sample_rate
        self._device = device
        self._max_frames = int(sample_rate * max_seconds)

        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._frame_count = 0
        self._lock = threading.Lock()
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        self._frames = []
        self._frame_count = 0
        self._recording = True

        def _callback(indata, frame_count, time_info, status):  # noqa: ARG001
            with self._lock:
                if not self._recording:
                    return
                self._frames.append(indata.copy())
                self._frame_count += frame_count
                if self._frame_count >= self._max_frames:
                    self._recording = False
                    raise sd.CallbackStop()

        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="int16",
            device=self._device,
            callback=_callback,
        )
        self._stream.start()

    def stop(self) -> str | None:
        """Stops recording and writes the captured audio to a temp WAV
        file, returning its path. Returns None if nothing meaningful was
        captured (e.g. stopped almost instantly)."""
        with self._lock:
            self._recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._frames:
            return None

        audio = np.concatenate(self._frames, axis=0)
        if len(audio) < self._sample_rate * 0.2:  # less than ~200ms — not a real utterance
            return None

        out_path = tempfile.mktemp(suffix=".wav")
        sf.write(out_path, audio, self._sample_rate, subtype="PCM_16")
        return out_path

    def cancel(self) -> None:
        """Stops recording and discards the buffer — no file is written."""
        with self._lock:
            self._recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._frames = []
