"""Human approval workflow for Foundry CLI commands."""

from __future__ import annotations

from typing import Any

from internal_tools.ogm_foundry.runtime import FoundryServices
from internal_tools.ogm_milestone_001.utils import prefixed_uuid


def approve_candidate(
    services: FoundryServices,
    candidate_id: str,
    *,
    actor: str,
    notes: str,
) -> dict[str, Any]:
    candidate = services.queue.get_candidate(candidate_id)
    if candidate["status"] == "rejected":
        raise PermissionError("rejected candidates cannot be approved")
    if candidate["status"] not in {"recommended", "approved_for_intake"}:
        raise PermissionError("candidate must be recommended before human approval")
    recommendation_id = candidate.get("curator_recommendation_id")
    if not recommendation_id:
        raise PermissionError("candidate requires a curator recommendation before approval")

    recommendation = services.records.get_curator_recommendation(recommendation_id)
    approval_id = prefixed_uuid("approval")
    approval = services.records.create_human_approval(
        approval_id=approval_id,
        mission_id=candidate["mission_id"],
        recommendation_id=recommendation_id,
        approver_id=actor,
        decision="approved",
        target_type="source_intake",
        target_id=candidate_id,
        metadata={"notes": notes},
    )
    updated = services.queue.update_candidate_review(
        candidate_id,
        status="approved_for_intake",
        actor=actor,
        reason="approved by human reviewer",
        reviewer_notes=notes,
        metadata={
            "approval_id": approval_id,
            "recommendation_id": recommendation_id,
        },
    )
    return {
        "candidate_id": candidate_id,
        "candidate_status": updated["status"],
        "recommendation_id": recommendation["recommendation_id"],
        "approval_id": approval["approval_id"],
        "approver_id": actor,
        "notes": notes,
    }
