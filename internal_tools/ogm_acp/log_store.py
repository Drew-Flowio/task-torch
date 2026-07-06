"""Append-only ACP log store with replay support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from internal_tools.ogm_acp.envelope import ACPMessage
from internal_tools.ogm_acp.errors import ACPError


class ACPLogStore:
    """Immutable JSONL message log."""

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def append(self, message: ACPMessage) -> None:
        line = message.to_json()
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def append_dict(self, data: dict[str, Any]) -> ACPMessage:
        message = ACPMessage.from_dict(data)
        self.append(message)
        return message

    def iter_messages(self) -> Iterator[ACPMessage]:
        if not self.log_path.exists():
            return iter(())

        def _generator() -> Iterator[ACPMessage]:
            with self.log_path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        yield ACPMessage.from_dict(json.loads(stripped))
                    except Exception as exc:  # pragma: no cover - defensive replay guard
                        raise ACPError(
                            "consumer_error",
                            f"Failed to replay line {line_number}",
                            retryable=False,
                            details={"line_number": line_number},
                        ) from exc

        return _generator()

    def replay(
        self,
        *,
        mission_id: str | None = None,
        message_type: str | None = None,
        agent_id: str | None = None,
        department: str | None = None,
        correlation_id: str | None = None,
    ) -> list[ACPMessage]:
        results: list[ACPMessage] = []
        for message in self.iter_messages():
            if mission_id is not None and message.mission_id != mission_id:
                continue
            if message_type is not None and message.message_type != message_type:
                continue
            if agent_id is not None and message.agent_id != agent_id:
                continue
            if department is not None and message.department != department:
                continue
            if correlation_id is not None:
                refs = message.references or {}
                if refs.get("correlation_id") != correlation_id:
                    continue
            results.append(message)
        return results

    def get_by_id(self, message_id: str) -> ACPMessage | None:
        for message in self.iter_messages():
            if message.message_id == message_id:
                return message
        return None

    def count(self) -> int:
        return sum(1 for _ in self.iter_messages())
