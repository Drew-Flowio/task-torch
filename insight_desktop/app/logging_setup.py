"""Local, lightweight logging for the Insight desktop app.

No network sink, ever. Logs go to a rotating local file (plus the
console) at the level set in `config/config.yaml`. This is a
personality-development tool running entirely on your machine, so
transcript text may be logged locally (see `logging.log_transcripts` in
config) - raw audio is never written to disk by any part of this app
(see `engine/interface.py`, which deletes the temp recording immediately
after transcription).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.loader import AppConfig

_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "error": logging.ERROR,
}


def setup_logging(config: AppConfig) -> None:
    log_dir = Path(config.resolve(config.logging.log_dir))
    log_dir.mkdir(parents=True, exist_ok=True)
    level = _LEVELS.get(config.logging.level.lower(), logging.INFO)

    root = logging.getLogger("insight")
    root.setLevel(level)
    root.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = RotatingFileHandler(
        log_dir / "insight_app.log", maxBytes=10 * 1024 * 1024, backupCount=5,
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)
