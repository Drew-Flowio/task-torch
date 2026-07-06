"""Loads config/config.yaml into a small set of typed, immutable config
objects, resolving every relative path against the repo root so this app
can sit next to `poc/`, `models/`, and `vendor/` and reuse them directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
INSIGHT_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = INSIGHT_DESKTOP_ROOT / "config" / "config.yaml"


@dataclass(frozen=True)
class UiConfig:
    mode: str = "desktop"  # desktop | touch
    screen_inches: int = 7
    fullscreen: bool = False
    brand_name: str = "Offgrid Minds"


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
    tts_length_scale: float = 0.91
    tts_noise_scale: float = 0.78
    tts_noise_w: float = 0.88
    vision_enabled: bool = True
    mtmd_cli_path: str = ""
    vision_model_path: str = ""
    vision_mmproj_path: str = ""
    vision_n_predict: int = 128
    vision_temperature: float = 0.1
    vision_gpu_layers: int = 0


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
    ui: UiConfig
    repo_root: Path = field(default=REPO_ROOT)

    def resolve(self, relative_path: str) -> str:
        p = Path(relative_path)
        return str(p if p.is_absolute() else self.repo_root / p)


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    models_raw = raw["models"]
    models = ModelsConfig(
        llm_model_path=models_raw["llm_model_path"],
        llm_n_ctx=models_raw["llm_n_ctx"],
        llm_n_threads=models_raw["llm_n_threads"],
        llm_max_tokens=models_raw["llm_max_tokens"],
        llm_temperature=models_raw["llm_temperature"],
        llm_top_p=models_raw["llm_top_p"],
        whisper_cli_path=models_raw["whisper_cli_path"],
        whisper_model_path=models_raw["whisper_model_path"],
        whisper_threads=models_raw["whisper_threads"],
        tts_voice_model_path=models_raw["tts_voice_model_path"],
        tts_length_scale=float(models_raw.get("tts_length_scale", 0.91)),
        tts_noise_scale=float(models_raw.get("tts_noise_scale", 0.78)),
        tts_noise_w=float(models_raw.get("tts_noise_w", 0.88)),
        vision_enabled=bool(models_raw.get("vision_enabled", True)),
        mtmd_cli_path=models_raw.get("mtmd_cli_path", ""),
        vision_model_path=models_raw.get("vision_model_path", ""),
        vision_mmproj_path=models_raw.get("vision_mmproj_path", ""),
        vision_n_predict=int(models_raw.get("vision_n_predict", 128)),
        vision_temperature=float(models_raw.get("vision_temperature", 0.1)),
        vision_gpu_layers=int(models_raw.get("vision_gpu_layers", 0)),
    )

    ui_raw = raw.get("ui", {})
    ui = UiConfig(
        mode=str(ui_raw.get("mode", "desktop")),
        screen_inches=int(ui_raw.get("screen_inches", 7)),
        fullscreen=bool(ui_raw.get("fullscreen", False)),
        brand_name=str(ui_raw.get("brand_name", "Insight")),
    )

    return AppConfig(
        mock_mode=bool(raw["engine"]["mock_mode"]),
        models=models,
        audio=AudioConfig(**raw["audio"]),
        interaction=InteractionConfig(**raw["interaction"]),
        storage=StorageConfig(**raw["storage"]),
        prompts=PromptsConfig(**raw["prompts"]),
        logging=LoggingConfig(**raw["logging"]),
        ui=ui,
    )
