"""ACP error types."""

from __future__ import annotations


class ACPError(Exception):
    """Base error for ACP operations."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details,
        }


class ACPValidationError(ACPError):
    """Raised when an envelope or payload fails validation."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(
            "schema_invalid",
            message,
            retryable=False,
            details=details,
        )
