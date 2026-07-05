"""Loads config/config.yaml into a small set of typed, immutable config
objects, resolving every relative path against the repo root so this app
can sit next to `poc/`, `models/`, and `vendor/` and reuse them directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# insight_desktop/config/loader.py -> parents[1] = insight_desktop/ -> parents[2] = repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
INSIGHT_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = INSIGHT_DESKTOP_ROOT / "config" / "config.yaml"


@dataclass(frozen=True)
class ModelsConfig:
    llm_model_path: str
    llm_n_ctx: int
    llm_n_threads: int
    llm_max_tokens: int
    llm_temperature: float
    llm_top_p: float
    whisper_cli_path: str
    whisper_model_path: str
    whisper_threads: int
    tts_voice_model_path: str


@dataclass(frozen=True)
class AudioConfig:
    sample_rate: int
    max_recording_seconds: int
    input_device: int | str | None
    output_device: int | str | None


@dataclass(frozen=True)
class InteractionConfig:
    assistant_name: str
    history_turns_in_prompt: int


@dataclass(frozen=True)
class StorageConfig:
    db_path: str


@dataclass(frozen=True)
class PromptsConfig:
    system_prompt_path: str


@dataclass(frozen=True)
class LoggingConfig:
    log_dir: str
    level: str
    log_transcripts: bool


@dataclass(frozen=True)
class AppConfig:
    mock_mode: bool
    models: ModelsConfig
    audio: AudioConfig
    interaction: InteractionConfig
    storage: StorageConfig
    prompts: PromptsConfig
    logging: LoggingConfig
    repo_root: Path = field(default=REPO_ROOT)

    def resolve(self, relative_path: str) -> str:
        """Resolves a config path (relative to the repo root) to an
        absolute path string."""
        p = Path(relative_path)
        return str(p if p.is_absolute() else self.repo_root / p)


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return AppConfig(
        mock_mode=bool(raw["engine"]["mock_mode"]),
        models=ModelsConfig(**raw["models"]),
        audio=AudioConfig(**raw["audio"]),
        interaction=InteractionConfig(**raw["interaction"]),
        storage=StorageConfig(**raw["storage"]),
        prompts=PromptsConfig(**raw["prompts"]),
        logging=LoggingConfig(**raw["logging"]),
    )
