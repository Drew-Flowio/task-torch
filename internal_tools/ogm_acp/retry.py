"""ACP retry policy helpers."""

from __future__ import annotations

from dataclasses import dataclass

from internal_tools.ogm_acp.envelope import ACPMessage


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 5
    initial_backoff_ms: int = 1000
    backoff_multiplier: float = 2.0
    max_backoff_ms: int = 60000
    retryable_error_codes: frozenset[str] = frozenset(
        {
            "transport_timeout",
            "consumer_busy",
            "transient_store_error",
        }
    )
    non_retryable_error_codes: frozenset[str] = frozenset(
        {
            "policy_violation",
            "schema_invalid",
            "forbidden_source",
            "approval_denied",
        }
    )

    def backoff_ms(self, retry_count: int) -> int:
        if retry_count <= 0:
            return self.initial_backoff_ms
        delay = int(self.initial_backoff_ms * (self.backoff_multiplier ** (retry_count - 1)))
        return min(delay, self.max_backoff_ms)


def should_retry(message: ACPMessage, policy: RetryPolicy | None = None) -> bool:
    policy = policy or RetryPolicy()
    if message.retry_count >= policy.max_retries:
        return False

    if not message.errors:
        return message.status == "failed"

    for error in message.errors:
        code = error.get("code", "")
        if code in policy.non_retryable_error_codes:
            return False
        if error.get("retryable") is False:
            return False

    return any(
        error.get("code") in policy.retryable_error_codes or error.get("retryable") is True
        for error in message.errors
    )
