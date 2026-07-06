"""ACP message envelope construction and serialization."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from internal_tools.ogm_acp.constants import ACP_VERSION
from internal_tools.ogm_acp.validation import validate_envelope_dict, validate_payload


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_message_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"msg:{stamp}:{uuid.uuid4().hex[:12]}"


@dataclass
class ACPMessage:
    version: str
    message_id: str
    timestamp: str
    message_type: str
    agent_id: str
    department: str
    mission_id: str
    priority: str
    status: str
    payload: dict[str, Any]
    references: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    to_department: str | None = None
    to_agent_id: str | None = None
    requires_ack: bool = False
    ttl_seconds: int | None = None
    trace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {key: value for key, value in data.items() if value is not None}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ACPMessage":
        validate_envelope_dict(data)
        validate_payload(data["message_type"], data.get("payload", {}))
        known = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {key: value for key, value in data.items() if key in known}
        return cls(**kwargs)

    @classmethod
    def from_json(cls, raw: str) -> "ACPMessage":
        return cls.from_dict(json.loads(raw))

    def with_status(self, status: str) -> "ACPMessage":
        updated = self.to_dict()
        updated["status"] = status
        return ACPMessage.from_dict(updated)

    def with_error(self, error: dict[str, Any], *, status: str = "failed") -> "ACPMessage":
        updated = self.to_dict()
        updated["status"] = status
        updated["errors"] = list(updated.get("errors", [])) + [error]
        return ACPMessage.from_dict(updated)

    def increment_retry(self) -> "ACPMessage":
        updated = self.to_dict()
        updated["retry_count"] = int(updated.get("retry_count", 0)) + 1
        updated["status"] = "pending"
        return ACPMessage.from_dict(updated)


def create_message(
    *,
    message_type: str,
    agent_id: str,
    department: str,
    mission_id: str,
    payload: dict[str, Any] | None = None,
    priority: str = "medium",
    status: str = "pending",
    references: dict[str, Any] | None = None,
    errors: list[dict[str, Any]] | None = None,
    retry_count: int = 0,
    to_department: str | None = None,
    to_agent_id: str | None = None,
    requires_ack: bool = False,
    ttl_seconds: int | None = None,
    trace_id: str | None = None,
    message_id: str | None = None,
    timestamp: str | None = None,
) -> ACPMessage:
    message = ACPMessage(
        version=ACP_VERSION,
        message_id=message_id or new_message_id(),
        timestamp=timestamp or utc_now_iso(),
        message_type=message_type,
        agent_id=agent_id,
        department=department,
        mission_id=mission_id,
        priority=priority,
        status=status,
        payload=payload or {},
        references=references or {},
        errors=errors or [],
        retry_count=retry_count,
        to_department=to_department,
        to_agent_id=to_agent_id,
        requires_ack=requires_ack,
        ttl_seconds=ttl_seconds,
        trace_id=trace_id,
    )
    validate_envelope_dict(message.to_dict())
    validate_payload(message_type, message.payload)
    return message
