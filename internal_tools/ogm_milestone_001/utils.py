"""Shared utilities for Milestone 1."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_uuid() -> str:
    return str(uuid.uuid4())


def prefixed_uuid(prefix: str) -> str:
    return f"{prefix}:{new_uuid()}"


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_mime_type(path: str | Path) -> str:
    mime_type, _encoding = mimetypes.guess_type(str(path))
    return mime_type or "application/octet-stream"


def json_dumps(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def json_loads(raw: str | None, default: Any) -> Any:
    if raw in (None, ""):
        return default
    return json.loads(raw)


def ensure_relative_name(filename: str) -> str:
    name = Path(filename).name
    if not name:
        raise ValueError("filename must not be empty")
    return name
