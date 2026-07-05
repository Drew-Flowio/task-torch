"""Adapts Piper into the engine's text-to-speech interface.

Same voice/engine already validated in poc/tts.py and
docs/07-voice-poc.md, but called through Piper's in-process Python API
(`piper.PiperVoice`) rather than shelling out to a CLI, and played back
with `sounddevice` instead of a platform-specific player like `afplay` —
this keeps playback working unchanged on macOS, Linux/Pi, and Windows.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import sounddevice as sd
from piper import PiperVoice


@dataclass(frozen=True)
class TtsConfig:
    voice_model_path: str  # the matching .onnx.json must sit alongside this file


class TtsAdapterProtocol(Protocol):
    def speak(self, text: str) -> None: ...
    def stop(self) -> None: ...


class TtsAdapter:
    """Loads a Piper voice once, then synthesizes and plays speech
    on demand. `speak()` blocks until playback finishes (or `stop()` is
    called from another thread to cut it short — that's what backs the
    app's Stop/Cancel button while Insight is talking)."""

    def __init__(self, config: TtsConfig):
        self._voice = PiperVoice.load(config.voice_model_path)
        self._sample_rate = self._voice.config.sample_rate
        self._stop_event = threading.Event()

    def speak(self, text: str) -> None:
        self._stop_event.clear()
        chunks = [chunk.audio_int16_array for chunk in self._voice.synthesize(text)]
        if not chunks:
            return
        audio = np.concatenate(chunks, axis=0)

        sd.play(audio, samplerate=self._sample_rate)
        # Poll in short slices instead of a single sd.wait() so stop() can
        # interrupt playback promptly rather than waiting for it to finish.
        while sd.get_stream().active:
            if self._stop_event.wait(timeout=0.05):
                sd.stop()
                break

    def stop(self) -> None:
        self._stop_event.set()
        sd.stop()
