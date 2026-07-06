"""Primary interaction modes for Offgrid Minds field UI."""

from __future__ import annotations

from enum import Enum


class AppMode(str, Enum):
    SCAN = "scan"
    TALK = "talk"
    CHAT = "chat"
