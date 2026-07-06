"""In-process ACP message bus."""

from __future__ import annotations

from typing import Callable

from internal_tools.ogm_acp.envelope import ACPMessage, create_message
from internal_tools.ogm_acp.errors import ACPError
from internal_tools.ogm_acp.log_store import ACPLogStore
from internal_tools.ogm_acp.registry import AgentRegistry
from internal_tools.ogm_acp.retry import RetryPolicy, should_retry
from internal_tools.ogm_acp.router import MissionRouter

MessageHandler = Callable[[ACPMessage], None]


class ACPBus:
    """Transport-agnostic in-process bus with logging, routing, and retry support."""

    def __init__(
        self,
        log_store: ACPLogStore,
        *,
        registry: AgentRegistry | None = None,
        router: MissionRouter | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.log_store = log_store
        self.registry = registry or AgentRegistry()
        self.router = router or MissionRouter(self.registry)
        self.retry_policy = retry_policy or RetryPolicy()
        self._global_handlers: list[MessageHandler] = []

    def subscribe(self, handler: MessageHandler) -> None:
        self._global_handlers.append(handler)

    def publish(self, message: ACPMessage) -> ACPMessage:
        outgoing = message.with_status("sent")
        self.log_store.append(outgoing)

        try:
            delivered = outgoing.with_status("delivered")
            self.log_store.append(delivered)
            self._dispatch(delivered)
            return delivered
        except ACPError as exc:
            failed = outgoing.with_error(exc.to_dict(), status="failed")
            self.log_store.append(failed)
            if should_retry(failed, self.retry_policy):
                retry_message = failed.increment_retry()
                self.log_store.append(retry_message)
                return self.publish(retry_message)
            dead_letter = failed.with_status("dead_letter")
            self.log_store.append(dead_letter)
            self._emit_system_message(
                message_type="MessageDeadLettered",
                source=dead_letter,
                payload={"original_message_id": dead_letter.message_id},
            )
            return dead_letter
        except Exception as exc:
            wrapped = ACPError("consumer_error", str(exc), retryable=True)
            failed = outgoing.with_error(wrapped.to_dict(), status="failed")
            self.log_store.append(failed)
            if should_retry(failed, self.retry_policy):
                retry_message = failed.increment_retry()
                self.log_store.append(retry_message)
                return self.publish(retry_message)
            dead_letter = failed.with_status("dead_letter")
            self.log_store.append(dead_letter)
            return dead_letter

    def acknowledge(self, message: ACPMessage) -> ACPMessage:
        acked = message.with_status("acknowledged")
        self.log_store.append(acked)
        self._emit_system_message(
            message_type="MessageAcknowledged",
            source=acked,
            payload={"acknowledged_message_id": message.message_id},
        )
        return acked

    def replay(
        self,
        *,
        mission_id: str | None = None,
        message_type: str | None = None,
        agent_id: str | None = None,
        department: str | None = None,
        correlation_id: str | None = None,
        redispatch: bool = False,
    ) -> list[ACPMessage]:
        messages = self.log_store.replay(
            mission_id=mission_id,
            message_type=message_type,
            agent_id=agent_id,
            department=department,
            correlation_id=correlation_id,
        )
        replayed: list[ACPMessage] = []
        for message in messages:
            replay_record = message.with_status("replayed")
            self.log_store.append(replay_record)
            replayed.append(replay_record)
            if redispatch:
                self._dispatch(replay_record)
        return replayed

    def _dispatch(self, message: ACPMessage) -> None:
        for handler in self._global_handlers:
            handler(message)
        self.router.route(message)

    def _emit_system_message(
        self,
        *,
        message_type: str,
        source: ACPMessage,
        payload: dict,
    ) -> None:
        system_message = create_message(
            message_type=message_type,
            agent_id="agent:system:bus",
            department="system",
            mission_id=source.mission_id,
            payload=payload,
            references={
                "reply_to": source.message_id,
                "correlation_id": source.references.get("correlation_id"),
            },
            status="sent",
        )
        self.log_store.append(system_message)
