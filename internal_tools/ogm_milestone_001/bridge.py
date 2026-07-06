"""Intake-to-Repository bridge for Milestone 2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from internal_tools.ogm_milestone_001.acp_events import (
    emit_acp_events,
    prepare_evidence_linked_event,
    prepare_source_acquired_event,
)
from internal_tools.ogm_milestone_001.coverage import CoverageStore
from internal_tools.ogm_milestone_001.intake_ledger import IntakeLedger
from internal_tools.ogm_milestone_001.knowledge_repository import KnowledgeRepository
from internal_tools.ogm_milestone_001.raw_source_vault import RawSourceVault


def bridge_intake_to_repository(
    *,
    ledger: IntakeLedger,
    repository: KnowledgeRepository,
    source_uuid: str,
    revision_uuid: str,
    coverage_store: CoverageStore | None = None,
    vault: RawSourceVault | None = None,
    actor: str = "system",
    acp_log_path: str | Path | None = None,
    acp_log_store: Any | None = None,
) -> dict[str, Any]:
    """Create repository evidence from an approved vaulted source revision.

    This bridge does not perform OCR or extraction. It preserves provenance
    from the intake ledger and links evidence back to the raw source revision.
    """

    source = ledger.get_source(source_uuid)
    if source["approval_status"] != "approved":
        raise ValueError("only approved sources can be bridged to the repository")

    revision = ledger.get_revision(revision_uuid)
    if revision["source_uuid"] != source_uuid:
        raise ValueError("revision does not belong to the provided source")

    if vault is not None and not vault.verify_revision(revision_uuid):
        raise ValueError("vault revision checksum verification failed")

    coverage_object_ids = list(source.get("coverage_object_ids") or [])
    mission_id = source.get("mission_id") or source["mission"]

    if coverage_store is not None:
        for coverage_object_id in coverage_object_ids:
            coverage_store.get_coverage_object(coverage_object_id)
            coverage_store.link_source_to_coverage(source_uuid, coverage_object_id)

    provenance = {
        "mission_id": mission_id,
        "curator": source["curator"],
        "curator_recommendation_id": source.get("curator_recommendation_id"),
        "human_approval_id": source.get("human_approval_id"),
        "source_uuid": source_uuid,
        "raw_revision_uuid": revision_uuid,
        "vault_path": revision["vault_path"],
        "checksum": revision["checksum"],
        "source_quality_score": source.get("source_quality_score"),
        "canonical_reference_type": source.get("canonical_reference_type"),
        "coverage_object_ids": coverage_object_ids,
        "license": source["license"],
        "bridge_stage": "intake_to_repository",
    }

    locator = {
        "type": "raw_source",
        "source_uuid": source_uuid,
        "revision_uuid": revision_uuid,
        "vault_path": revision["vault_path"],
        "filename": revision["filename"],
    }
    citation = {
        "title": source["filename"],
        "source_id": source_uuid,
        "source_label": source["source"],
        "locator": f"raw revision {revision_uuid}",
        "license": source["license"],
    }

    evidence = repository.create_evidence(
        source_uuid=source_uuid,
        raw_revision_uuid=revision_uuid,
        locator=locator,
        citation=citation,
        metadata={"provenance": provenance},
        actor=actor,
    )

    if coverage_store is not None:
        for coverage_object_id in coverage_object_ids:
            coverage_store.link_evidence_to_coverage(evidence["evidence_uuid"], coverage_object_id)

    ledger.update_processing_state(source_uuid, "evidence_linked", actor=actor)
    repository.record_audit(
        action="intake_bridged_to_repository",
        entity_type="evidence",
        entity_id=evidence["evidence_uuid"],
        actor=actor,
        details={
            "source_uuid": source_uuid,
            "revision_uuid": revision_uuid,
            "coverage_object_ids": coverage_object_ids,
        },
    )

    acp_events = [
        prepare_source_acquired_event(
            source_uuid=source_uuid,
            revision_uuid=revision_uuid,
            mission_id=mission_id,
            coverage_object_ids=coverage_object_ids,
            curator_recommendation_id=source.get("curator_recommendation_id"),
            human_approval_id=source.get("human_approval_id"),
        ),
        prepare_evidence_linked_event(
            evidence_uuid=evidence["evidence_uuid"],
            source_uuid=source_uuid,
            raw_revision_uuid=revision_uuid,
            mission_id=mission_id,
            coverage_object_ids=coverage_object_ids,
        ),
    ]
    emit_acp_events(acp_events, log_path=acp_log_path, log_store=acp_log_store)

    return {
        "source": source,
        "revision": revision,
        "evidence": evidence,
        "provenance": provenance,
        "coverage_object_ids": coverage_object_ids,
        "acp_events": acp_events,
    }
