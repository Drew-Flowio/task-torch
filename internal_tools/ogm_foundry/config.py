"""Foundry runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_ROOT = PACKAGE_ROOT / "data"


@dataclass(frozen=True)
class FoundryConfig:
    data_root: Path
    intake_db: Path
    repository_db: Path
    vault_root: Path
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "FoundryConfig":
        data_root = Path(os.environ.get("OGM_FOUNDRY_ROOT", DEFAULT_DATA_ROOT))
        return cls(
            data_root=data_root,
            intake_db=Path(os.environ.get("OGM_FOUNDRY_INTAKE_DB", data_root / "intake.db")),
            repository_db=Path(os.environ.get("OGM_FOUNDRY_REPOSITORY_DB", data_root / "repository.db")),
            vault_root=Path(os.environ.get("OGM_FOUNDRY_VAULT_ROOT", data_root / "vault")),
            host=os.environ.get("OGM_FOUNDRY_HOST", "127.0.0.1"),
            port=int(os.environ.get("OGM_FOUNDRY_PORT", "8790")),
        )
