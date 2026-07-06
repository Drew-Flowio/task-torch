"""Mission-aware ACP message routing."""

from __future__ import annotations

from typing import Callable

from internal_tools.ogm_acp.constants import DEFAULT_ROUTE_TABLE
from internal_tools.ogm_acp.envelope import ACPMessage
from internal_tools.ogm_acp.registry import AgentRegistry


RouteHandler = Callable[[ACPMessage], None]


class MissionRouter:
    """Routes messages to departments and registered agents."""

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        route_table: dict[str, str] | None = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.route_table = dict(route_table or DEFAULT_ROUTE_TABLE)
        self._department_handlers: dict[str, list[RouteHandler]] = {}
        self._agent_handlers: dict[str, list[RouteHandler]] = {}

    def subscribe_department(self, department: str, handler: RouteHandler) -> None:
        self._department_handlers.setdefault(department, []).append(handler)

    def subscribe_agent(self, agent_id: str, handler: RouteHandler) -> None:
        self._agent_handlers.setdefault(agent_id, []).append(handler)

    def resolve_destination(self, message: ACPMessage) -> tuple[str | None, str | None]:
        if message.to_agent_id:
            return message.to_department, message.to_agent_id

        if message.to_department:
            return message.to_department, None

        department = self.route_table.get(message.message_type)
        if department:
            return department, None

        return None, None

    def route(self, message: ACPMessage) -> list[str]:
        department, agent_id = self.resolve_destination(message)
        delivered: list[str] = []

        if agent_id:
            for handler in self._agent_handlers.get(agent_id, []):
                handler(message)
            delivered.append(f"agent:{agent_id}")

        if department:
            for handler in self._department_handlers.get(department, []):
                handler(message)
            delivered.append(f"department:{department}")

        return delivered

    def available_agents_for(self, message: ACPMessage) -> list[str]:
        department, agent_id = self.resolve_destination(message)
        if agent_id:
            record_on = self.registry.get(agent_id)
            if record and not self.registry.is_stale(agent_id):
                return [agent_id]
            return []

        if not department:
            return []

        return [
            record.agent_id
            for record in self.registry.list_agents(department=department, available_only=True)
        ]
