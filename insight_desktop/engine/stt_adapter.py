"""Adapts whisper.cpp into the engine's speech-to-text interface.

Same engine and pattern already validated in poc/stt.py and
docs/07-voice-poc.md — this is that same proven local, offline STT path,
generalized as a class the desktop engine can hold onto.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SttConfig:
    whisper_cli_path: str
    model_path: str
    threads: int = 8
    language: str = "en"


class SttAdapterProtocol(Protocol):
    def transcribe(self, audio_path: str) -> str: ...


class SttAdapter:
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
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return " ".join(lines).strip()
