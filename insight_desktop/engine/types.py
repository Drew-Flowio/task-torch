"""Small shared types passed across the engine <-> UI boundary.

Nothing in this file depends on Qt or on any specific model runtime —
that's the point. The UI layer translates these into Qt signals; the
engine layer never imports Qt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AppState(str, Enum):
    """Every state the status area in the UI can show."""

    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class SessionStateView:
    """A read-only snapshot of engine state for the inspector panel."""

    session_id: str
    message_count: int
    active_prompt_label: str | None
    active_prompt_version_id: str | None
    memory_fact_count: int
    current_state: AppState
    session_summary: str


@dataclass
class TurnResult:
    """What a completed (or cancelled) turn produced."""

    transcript: str | None      # only set for voice turns
    reply_text: str
    cancelled: bool
    latency_ms: int
    prompt_version_id: str | None
    assembled_prompt_debug: str = field(default="")  # exact messages sent to the LLM, for the inspector
