"""Workspace status reporting helpers."""

from __future__ import annotations

from typing import Any

from internal_tools.ogm_foundry.data import FoundryDataReader
from internal_tools.ogm_foundry.runtime import FoundryServices, ensure_workspace


def workspace_status(services: FoundryServices) -> dict[str, Any]:
    reader = FoundryDataReader(services.config)
    summary = reader.dashboard_summary()
    candidates = services.queue.list_candidates()
    by_status: dict[str, int] = {}
    for candidate in candidates:
        by_status[candidate["status"]] = by_status.get(candidate["status"], 0) + 1

    recommendations = services.records.list_curator_recommendations()
    approvals = services.records.list_human_approvals(decision="approved")

    next_actions: list[str] = []
    if summary["missions"]["total"] == 0:
        next_actions.append("Bootstrap the workspace: python3 -m internal_tools.ogm_foundry.bootstrap_workspace")
    if by_status.get("submitted", 0):
        next_actions.append(
            "Evaluate submitted candidates: python3 -m internal_tools.ogm_foundry.evaluate_candidates"
        )
    if by_status.get("recommended", 0):
        next_actions.append(
            "Approve recommended candidates: python3 -m internal_tools.ogm_foundry.approve_candidate <candidate_id> --actor <name> --notes <reason>"
        )
    if by_status.get("approved_for_intake", 0):
        next_actions.append(
            "Intake approved local-file candidates: python3 -m internal_tools.ogm_foundry.intake_approved_candidate <candidate_id>"
        )
    if not candidates and summary["missions"]["total"]:
        next_actions.append(
            "Import real candidates from CSV: python3 -m internal_tools.ogm_foundry.import_candidates <path/to/candidates.csv>"
        )
    if not next_actions:
        next_actions.append("Review dashboard coverage and continue sourcing missing CRS requirements.")

    return {
        "workspace": {
            "data_root": str(services.config.data_root),
            "intake_db": str(services.config.intake_db),
            "repository_db": str(services.config.repository_db),
            "vault_root": str(services.config.vault_root),
        },
        "counts": {
            "missions": summary["missions"]["total"],
            "coverage_objects": summary["coverage"]["total"],
            "crs_requirements": summary["crs_requirements"]["total_requirements"],
            "candidates_total": len(candidates),
            "candidates_by_status": by_status,
            "recommendations": len(recommendations),
            "approvals": len(approvals),
            "vault_sources": summary["vault"]["sources"],
            "evidence": summary["repository"]["evidence"],
            "knowledge_objects": summary["repository"]["knowledge_objects"],
        },
        "coverage": summary["coverage"]["items"],
        "crs_requirements": summary["crs_requirements"]["items"],
        "next_actions": next_actions,
    }


def format_workspace_status(payload: dict[str, Any]) -> str:
    lines = [
        "Offgrid Minds Foundry Workspace Status",
        f"Data root: {payload['workspace']['data_root']}",
        "",
        "Counts",
        f"  Missions: {payload['counts']['missions']}",
        f"  Coverage objects: {payload['counts']['coverage_objects']}",
        f"  CRS requirements: {payload['counts']['crs_requirements']}",
        f"  Candidates: {payload['counts']['candidates_total']}",
        f"  Recommendations: {payload['counts']['recommendations']}",
        f"  Approvals: {payload['counts']['approvals']}",
        f"  Vault sources: {payload['counts']['vault_sources']}",
        f"  Evidence: {payload['counts']['evidence']}",
        f"  Knowledge objects: {payload['counts']['knowledge_objects']}",
        "",
        "Candidates by status",
    ]
    for status, count in sorted(payload["counts"]["candidates_by_status"].items()):
        lines.append(f"  {status}: {count}")
    lines.extend(["", "Coverage"])
    for item in payload["coverage"]:
        lines.append(
            f"  {item['title']}: {item.get('coverage_percentage', 0.0):.1%} ({item.get('status', 'unknown')})"
        )
    lines.extend(["", "Next actions"])
    for action in payload["next_actions"]:
        lines.append(f"  - {action}")
    return "\n".join(lines)


def load_status(config=None) -> dict[str, Any]:
    from internal_tools.ogm_foundry.config import FoundryConfig
    from internal_tools.ogm_foundry.runtime import load_services

    config = config or FoundryConfig.from_env()
    ensure_workspace(config)
    return workspace_status(load_services(config))
