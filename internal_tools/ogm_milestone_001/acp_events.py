"""ACP event integration for Milestone 1/2/3 using the ogm_acp package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from internal_tools.ogm_acp import ACPLogStore, create_message
from internal_tools.ogm_acp.envelope import ACPMessage


def prepare_source_acquired_event(
    *,
    source_uuid: str,
    revision_uuid: str,
    mission_id: str,
    coverage_object_ids: list[str],
    curator_recommendation_id: str | None = None,
    human_approval_id: str | None = None,
) -> ACPMessage:
    return create_message(
        message_type="SourceAcquired",
        agent_id="agent:milestone-bridge:001",
        department="acquisition",
        mission_id=mission_id,
        payload={
            "source_uuid": source_uuid,
            "revision_uuid": revision_uuid,
            "coverage_object_ids": coverage_object_ids,
            "curator_recommendation_id": curator_recommendation_id,
            "human_approval_id": human_approval_id,
        },
        status="sent",
    )


def prepare_evidence_linked_event(
    *,
    evidence_uuid: str,
    source_uuid: str,
    raw_revision_uuid: str,
    mission_id: str,
    coverage_object_ids: list[str],
) -> ACPMessage:
    return create_message(
        message_type="EvidenceLinked",
        agent_id="agent:milestone-bridge:001",
        department="knowledge_engineering",
        mission_id=mission_id,
        payload={
            "evidence_uuid": evidence_uuid,
            "source_uuid": source_uuid,
            "raw_revision_uuid": raw_revision_uuid,
            "coverage_object_ids": coverage_object_ids,
        },
        status="sent",
    )


def prepare_repository_object_created_event(
    *,
    object_uuid: str,
    category: str,
    title: str,
    mission_id: str,
    evidence_refs: list[str],
) -> ACPMessage:
    return create_message(
        message_type="RepositoryObjectCreated",
        agent_id="agent:milestone-repository:001",
        department="knowledge_engineering",
        mission_id=mission_id,
        payload={
            "repository_object_id": object_uuid,
            "object_type": category,
            "title": title,
            "evidence_refs": evidence_refs,
        },
        status="sent",
    )


def prepare_crs_requirement_satisfied_event(
    *,
    coverage_object_id: str,
    reference_type: str,
    mission_id: str,
    requirement_id: str,
) -> ACPMessage:
    return create_message(
        message_type="CRSRequirementSatisfied",
        agent_id="agent:milestone-crs:001",
        department="cko",
        mission_id=mission_id,
        payload={
            "coverage_object_id": coverage_object_id,
            "reference_type": reference_type,
            "requirement_id": requirement_id,
        },
        status="sent",
    )


def prepare_crs_requirement_missing_event(
    *,
    coverage_object_id: str,
    reference_type: str,
    mission_id: str,
    requirement_id: str,
) -> ACPMessage:
    return create_message(
        message_type="CRSRequirementMissing",
        agent_id="agent:milestone-crs:001",
        department="cko",
        mission_id=mission_id,
        payload={
            "coverage_object_id": coverage_object_id,
            "reference_type": reference_type,
            "requirement_id": requirement_id,
        },
        status="sent",
    )


def prepare_coverage_mission_generated_event(
    *,
    mission_id: str,
    coverage_object_id: str,
    objective: str,
    missing_reference_types: list[str],
    suggestion_id: str,
) -> ACPMessage:
    return create_message(
        message_type="CoverageMissionGenerated",
        agent_id="agent:milestone-cko:001",
        department="cko",
        mission_id=mission_id,
        payload={
            "mission_id": mission_id,
            "coverage_object_id": coverage_object_id,
            "objective": objective,
            "missing_reference_types": missing_reference_types,
            "suggestion_id": suggestion_id,
        },
        status="sent",
    )


def emit_acp_events(
    events: list[ACPMessage | dict[str, Any]],
    log_path: str | Path | None = None,
    log_store: ACPLogStore | None = None,
) -> list[ACPMessage | dict[str, Any]]:
    """Append validated ACP messages to an ACPLogStore when provided."""

    store = log_store
    if store is None and log_path is not None:
        store = ACPLogStore(log_path)
    if store is None:
        return events

    for event in events:
        if isinstance(event, ACPMessage):
            store.append(event)
        else:
            store.append_dict(event)
    return events
