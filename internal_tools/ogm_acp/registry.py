"""Agent discovery registry for ACP routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from internal_tools.ogm_acp.envelope import ACPMessage, create_message, utc_now_iso


@dataclass
class AgentRecord:
    agent_id: str
    department: str
    role: str
    capabilities: list[str] = field(default_factory=list)
    status: str = "idle"
    endpoint: str | None = None
    registered_at: str = field(default_factory=utc_now_iso)
    last_heartbeat_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "department": self.department,
            "role": self.role,
            "capabilities": list(self.capabilities),
            "status": self.status,
            "endpoint": self.endpoint,
            "registered_at": self.registered_at,
            "last_heartbeat_at": self.last_heartbeat_at,
        }


class AgentRegistry:
    """In-process agent registry for v1 deployments."""

    def __init__(self, *, stale_after_seconds: int = 120) -> None:
        self._agents: dict[str, AgentRecord] = {}
        self.stale_after_seconds = stale_after_seconds

    def register(
        self,
        *,
        agent_id: str,
        department: str,
        role: str,
        capabilities: list[str] | None = None,
        endpoint: str | None = None,
        status: str = "idle",
    ) -> AgentRecord:
        record = AgentRecord(
            agent_id=agent_id,
            department=department,
            role=role,
            capabilities=capabilities or [],
            endpoint=endpoint,
            status=status,
        )
        self._agents[agent_id] = record
        return record

    def unregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def heartbeat(self, agent_id: str, *, status: str = "idle") -> AgentRecord:
        record = self._agents.get(agent_id)
        if record is None:
            raise KeyError(f"Unknown agent: {agent_id}")
        record.last_heartbeat_at = utc_now_iso()
        record.status = status
        return record

    def get(self, agent_id: str) -> AgentRecord | None:
        return self._agents.get(agent_id)

    def list_agents(
        self,
        *,
        department: str | None = None,
        available_only: bool = False,
    ) -> list[AgentRecord]:
        records = list(self._agents.values())
        if department is not None:
            records = [record for record in records if record.department == department]
        if available_only:
            records = [record for record in records if not self.is_stale(record.agent_id)]
        return records

    def is_stale(self, agent_id: str) -> bool:
        record = self._agents.get(agent_id)
        if record is None:
            return True
        if record.last_heartbeat_at is None:
            return False
        heartbeat = datetime.fromisoformat(record.last_heartbeat_at.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - heartbeat
        return age.total_seconds() > self.stale_after_seconds

    def registration_message(
        self,
        *,
        agent_id: str,
        department: str,
        role: str,
        mission_id: str = "mission:system",
        capabilities: list[str] | None = None,
        endpoint: str | None = None,
    ) -> ACPMessage:
        record = self.register(
            agent_id=agent_id,
            department=department,
            role=role,
            capabilities=capabilities,
            endpoint=endpoint,
        )
        return create_message(
            message_type="AgentRegistered",
            agent_id=agent_id,
            department=department,
            mission_id=mission_id,
            payload={
                "agent_id": record.agent_id,
                "department": record.department,
                "role": record.role,
                "capabilities": record.capabilities,
                "status": record.status,
                "endpoint": record.endpoint,
                "registered_at": record.registered_at,
            },
            references={"correlation_id": f"corr:{agent_id}:register"},
        )
