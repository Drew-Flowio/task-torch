"""The headset "ears": turns a recorded question (a WAV file, for now) into
text, using whisper.cpp.

Same pattern as vision.py: the only contract with the rest of the system is
`transcribe(path) -> str`. Swapping the whisper.cpp model size, or a
completely different STT engine later, only means changing this file.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class SttConfig:
    whisper_cli_path: str
    model_path: str
    threads: int = 4
    language: str = "en"


class SpeechToText:
    """Wraps the `whisper-cli` binary to transcribe a short WAV recording."""

    def __init__(self, config: SttConfig):
        self._config = config

    def transcribe(self, audio_path: str) -> str:
        cfg = self._config
        cmd = [
            cfg.whisper_cli_path,
            "-m", cfg.model_path,
            "-f", audio_path,
            "-l", cfg.language,
            "-t", str(cfg.threads),
            "-nt",  # no timestamps in stdout, easier to parse
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return " ".join(lines)
