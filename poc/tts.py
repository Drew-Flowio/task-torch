"""The headset "voice": turns the brain's answer text into a spoken WAV
file, using Piper.

Same pattern as vision.py and stt.py: the only contract with the rest of
the system is `speak(text) -> path_to_wav`. Swapping the Piper voice, or a
different TTS engine entirely, only means changing this file.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass


@dataclass
class TtsConfig:
    voice_model_path: str  # path to the .onnx voice file (matching .onnx.json must sit alongside it)
    python_executable: str = "python"


class TextToSpeech:
    """Wraps Piper (`python -m piper`) to synthesize speech to a WAV file."""

    def __init__(self, config: TtsConfig):
        self._config = config

    def speak(self, text: str, output_path: str | None = None) -> str:
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav")

        cfg = self._config
        cmd = [
            cfg.python_executable, "-m", "piper",
            "-m", cfg.voice_model_path,
            "--output_file", output_path,
        ]
        subprocess.run(
            cmd,
            input=text,
            text=True,
            capture_output=True,
            check=True,
        )
        return output_path
