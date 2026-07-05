"""Active photo context for the current conversation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VisualContext:
    image_path: str
    caption: str

    def prompt_block(self) -> str:
        return (
            "What the user is showing you (from their attached photo — "
            "keep this in mind for follow-up questions until they attach a new photo):\n"
            f"{self.caption}"
        )
