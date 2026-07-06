"""ACP envelope and payload validation."""

from __future__ import annotations

from typing import Any

from internal_tools.ogm_acp.constants import (
    ACP_VERSION,
    DEPARTMENTS,
    MESSAGE_STATUSES,
    MESSAGE_TYPES,
    PRIORITIES,
    REQUIRED_PAYLOAD_FIELDS,
)
from internal_tools.ogm_acp.errors import ACPValidationError

REQUIRED_ENVELOPE_FIELDS = (
    "version",
    "message_id",
    "timestamp",
    "message_type",
    "agent_id",
    "department",
    "mission_id",
    "priority",
    "status",
    "payload",
    "references",
    "errors",
    "retry_count",
)


def validate_envelope_dict(data: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_ENVELOPE_FIELDS if field not in data]
    if missing:
        raise ACPValidationError(
            f"Missing required envelope fields: {', '.join(missing)}",
            details={"missing": missing},
        )

    if data["version"] != ACP_VERSION:
        raise ACPValidationError(
            f"Unsupported ACP version: {data['version']}",
            details={"version": data["version"]},
        )

    if data["message_type"] not in MESSAGE_TYPES:
        raise ACPValidationError(
            f"Unknown message_type: {data['message_type']}",
            details={"message_type": data["message_type"]},
        )

    if data["department"] not in DEPARTMENTS:
        raise ACPValidationError(
            f"Unknown department: {data['department']}",
            details={"department": data["department"]},
        )

    if data["priority"] not in PRIORITIES:
        raise ACPValidationError(
            f"Unknown priority: {data['priority']}",
            details={"priority": data["priority"]},
        )

    if data["status"] not in MESSAGE_STATUSES:
        raise ACPValidationError(
            f"Unknown status: {data['status']}",
            details={"status": data["status"]},
        )

    if not isinstance(data["payload"], dict):
        raise ACPValidationError("payload must be an object")

    if not isinstance(data["references"], dict):
        raise ACPValidationError("references must be an object")

    if not isinstance(data["errors"], list):
        raise ACPValidationError("errors must be an array")

    retry_count = data["retry_count"]
    if not isinstance(retry_count, int) or retry_count < 0:
        raise ACPValidationError("retry_count must be a non-negative integer")

    to_department = data.get("to_department")
    if to_department is not None and to_department not in DEPARTMENTS:
        raise ACPValidationError(
            f"Unknown to_department: {to_department}",
            details={"to_department": to_department},
        )


def validate_payload(message_type: str, payload: dict[str, Any]) -> None:
    required = REQUIRED_PAYLOAD_FIELDS.get(message_type)
    if not required:
        return

    missing = [field for field in required if field not in payload]
    if missing:
        raise ACPValidationError(
            f"Missing required payload fields for {message_type}: {', '.join(missing)}",
            details={"message_type": message_type, "missing": missing},
        )
