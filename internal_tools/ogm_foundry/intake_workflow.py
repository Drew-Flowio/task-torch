"""Vault and repository intake workflow for Foundry CLI commands."""

from __future__ import annotations

from typing import Any

from internal_tools.ogm_foundry.runtime import FoundryServices
from internal_tools.ogm_milestone_001.orchestration import approved_candidate_to_repository_evidence


def intake_approved_candidate(
    services: FoundryServices,
    candidate_id: str,
    *,
    actor: str = "system",
    strict_license_review: bool = False,
) -> dict[str, Any]:
    candidate = services.queue.get_candidate(candidate_id)
    if candidate["status"] == "rejected":
        raise PermissionError("rejected candidates cannot be intaken")
    if candidate["status"] != "approved_for_intake":
        raise PermissionError("candidate must be approved_for_intake before vault intake")

    result = approved_candidate_to_repository_evidence(
        candidate_queue=services.queue,
        candidate_id=candidate_id,
        ledger=services.ledger,
        vault=services.vault,
        repository=services.repository,
        coverage_store=services.coverage,
        actor=actor,
        strict_license_review=strict_license_review,
        acp_log_store=services.acp_log,
    )
    evaluation = services.crs_evaluator.evaluate_and_record(candidate["coverage_object_id"])
    coverage = services.coverage.get_coverage_object(candidate["coverage_object_id"])
    return {
        **result,
        "coverage_object_id": candidate["coverage_object_id"],
        "coverage_status": coverage["status"],
        "coverage_percentage": coverage["coverage_percentage"],
        "crs_evaluation": evaluation,
    }
