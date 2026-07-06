"""Human review state transitions for repository objects and relationships."""

from __future__ import annotations

REVIEW_STATUSES = frozenset({"candidate", "needs_review", "approved", "rejected"})

# from_status -> allowed to_status values
OBJECT_TRANSITIONS: dict[str, frozenset[str]] = {
    "candidate": frozenset({"needs_review", "approved", "rejected"}),
    "needs_review": frozenset({"approved", "rejected"}),
    "approved": frozenset({"rejected", "needs_review"}),
    "rejected": frozenset({"needs_review"}),
}

RELATIONSHIP_TRANSITIONS = OBJECT_TRANSITIONS


def validate_transition(current_status: str, new_status: str, *, entity_label: str) -> None:
    if current_status not in REVIEW_STATUSES:
        raise ValueError(f"unknown {entity_label} status: {current_status}")
    if new_status not in REVIEW_STATUSES:
        raise ValueError(f"unknown target {entity_label} status: {new_status}")
    allowed = OBJECT_TRANSITIONS.get(current_status, frozenset())
    if new_status not in allowed:
        raise ValueError(
            f"invalid {entity_label} transition: {current_status} -> {new_status}; "
            f"rejected entities must return to needs_review before approval"
        )
