"""Append-only audit logging for Milestone 1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from internal_tools.ogm_milestone_001.utils import json_dumps, prefixed_uuid, utc_now_iso


class AuditLog:
    """Simple append-only JSONL audit log."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        actor: str = "system",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "audit_id": prefixed_uuid("audit"),
            "timestamp": utc_now_iso(),
            "actor": actor,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json_dumps(event) + "\n")
        return event

    def read_all(self) -> list[dict[str, Any]]:
        import json

        events: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    events.append(json.loads(line))
        return events
