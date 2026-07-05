"""Plain dataclasses for records read from / written to SQLite.

Kept separate from `repository.py` so the engine and UI layers can import
these shapes without importing sqlite3 anywhere outside `storage/`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Session:
    id: str
    started_at: str
    ended_at: str | None
    status: str  # active | ended


@dataclass(frozen=True)
class Message:
    id: str
    session_id: str
    ts: str
    role: str  # user | assistant | system
    content: str
    source: str  # text | voice
    prompt_version_id: str | None
    latency_ms: int | None
    cancelled: bool


@dataclass(frozen=True)
class PromptVersion:
    id: str
    content: str
    label: str | None
    created_at: str
    is_active: bool


@dataclass(frozen=True)
class MemoryFact:
    id: str
    text: str
    created_at: str
    active: bool
