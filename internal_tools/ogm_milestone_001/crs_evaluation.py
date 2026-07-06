"""CRS evaluation, coverage scoring, and mission suggestion generation."""

from __future__ import annotations

from typing import Any

from internal_tools.ogm_milestone_001.acp_events import (
    emit_acp_events,
    prepare_coverage_mission_generated_event,
    prepare_crs_requirement_missing_event,
    prepare_crs_requirement_satisfied_event,
)
from internal_tools.ogm_milestone_001.coverage import CoverageStore
from internal_tools.ogm_milestone_001.intake_ledger import IntakeLedger
from internal_tools.ogm_milestone_001.knowledge_repository import KnowledgeRepository


class CRSEvaluator:
    """Evaluates CRS requirement satisfaction and coverage completeness."""

    COMPLETE_THRESHOLD = 1.0

    def __init__(
        self,
        coverage_store: CoverageStore,
        *,
        ledger: IntakeLedger | None = None,
        repository: KnowledgeRepository | None = None,
        acp_log_store: Any | None = None,
    ) -> None:
        self.coverage_store = coverage_store
        self.ledger = ledger
        self.repository = repository
        self.acp_log_store = acp_log_store

    def list_requirements(self, coverage_object_id: str) -> list[dict[str, Any]]:
        return self.coverage_store.list_canonical_reference_requirements(coverage_object_id)

    def _linked_source_records(self, coverage_object_id: str) -> list[dict[str, Any]]:
        if self.ledger is None:
            return []
        sources: list[dict[str, Any]] = []
        for source_uuid in self.coverage_store.list_coverage_for_source_by_object(coverage_object_id):
            sources.append(self.ledger.get_source(source_uuid))
        return sources

    def _linked_evidence_records(self, coverage_object_id: str) -> list[dict[str, Any]]:
        if self.repository is None:
            return []
        evidence_records: list[dict[str, Any]] = []
        for evidence_uuid in self.coverage_store.list_coverage_for_evidence_by_object(coverage_object_id):
            evidence_records.append(self.repository.get_evidence(evidence_uuid))
        return evidence_records

    def _reference_types_present(self, coverage_object_id: str) -> dict[str, list[dict[str, Any]]]:
        present: dict[str, list[dict[str, Any]]] = {}

        for source in self._linked_source_records(coverage_object_id):
            ref_type = source.get("canonical_reference_type")
            if ref_type:
                present.setdefault(ref_type, []).append(
                    {"kind": "source", "source_uuid": source["uuid"], "evidence_uuid": None}
                )

        for evidence in self._linked_evidence_records(coverage_object_id):
            provenance = evidence.get("metadata", {}).get("provenance", {})
            ref_type = provenance.get("canonical_reference_type")
            if ref_type:
                present.setdefault(ref_type, []).append(
                    {
                        "kind": "evidence",
                        "source_uuid": evidence["source_uuid"],
                        "evidence_uuid": evidence["evidence_uuid"],
                    }
                )

        return present

    def evaluate_and_record(self, coverage_object_id: str) -> dict[str, Any]:
        """Evaluate CRS satisfaction and persist satisfaction records."""

        requirements = [req for req in self.list_requirements(coverage_object_id) if req["required"]]
        present = self._reference_types_present(coverage_object_id)
        satisfied_requirements: list[dict[str, Any]] = []
        missing_requirements: list[dict[str, Any]] = []
        acp_events = []

        for requirement in requirements:
            matches = present.get(requirement["reference_type"], [])
            if matches:
                match = matches[0]
                satisfaction = self.coverage_store.record_crs_satisfaction(
                    requirement_id=requirement["requirement_id"],
                    coverage_object_id=coverage_object_id,
                    reference_type=requirement["reference_type"],
                    source_uuid=match.get("source_uuid"),
                    evidence_uuid=match.get("evidence_uuid"),
                )
                satisfied_requirements.append({**requirement, "satisfaction": satisfaction})
                if self.acp_log_store is not None:
                    acp_events.append(
                        prepare_crs_requirement_satisfied_event(
                            coverage_object_id=coverage_object_id,
                            reference_type=requirement["reference_type"],
                            mission_id=self._mission_id_for_coverage(coverage_object_id),
                            requirement_id=requirement["requirement_id"],
                        )
                    )
            else:
                missing_requirements.append(requirement)
                if self.acp_log_store is not None:
                    acp_events.append(
                        prepare_crs_requirement_missing_event(
                            coverage_object_id=coverage_object_id,
                            reference_type=requirement["reference_type"],
                            mission_id=self._mission_id_for_coverage(coverage_object_id),
                            requirement_id=requirement["requirement_id"],
                        )
                    )

        emit_acp_events(acp_events, log_store=self.acp_log_store)

        score = self.score_coverage(coverage_object_id, satisfied_requirements, missing_requirements)
        self.coverage_store.update_coverage_status(
            coverage_object_id,
            score["status"],
            score["coverage_percentage"],
        )
        return {
            "coverage_object_id": coverage_object_id,
            "required_crs_count": score["required_crs_count"],
            "satisfied_crs_count": score["satisfied_crs_count"],
            "missing_crs_requirements": missing_requirements,
            "satisfied_crs_requirements": satisfied_requirements,
            "coverage_percentage": score["coverage_percentage"],
            "status": score["status"],
        }

    def score_coverage(
        self,
        coverage_object_id: str,
        satisfied_requirements: list[dict[str, Any]] | None = None,
        missing_requirements: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        requirements = [req for req in self.list_requirements(coverage_object_id) if req["required"]]
        required_crs_count = len(requirements)

        if satisfied_requirements is None or missing_requirements is None:
            present = self._reference_types_present(coverage_object_id)
            missing_requirements = [
                req for req in requirements if req["reference_type"] not in present
            ]
            satisfied_crs_count = required_crs_count - len(missing_requirements)
        else:
            satisfied_crs_count = len(satisfied_requirements)
            missing_requirements = missing_requirements

        if required_crs_count == 0:
            coverage_percentage = 0.0
            status = "not_started"
        else:
            coverage_percentage = round(satisfied_crs_count / required_crs_count, 4)
            if coverage_percentage >= self.COMPLETE_THRESHOLD:
                status = "complete"
            elif coverage_percentage > 0:
                status = "partial"
            else:
                status = "not_started"

        return {
            "coverage_object_id": coverage_object_id,
            "required_crs_count": required_crs_count,
            "satisfied_crs_count": satisfied_crs_count,
            "missing_crs_requirements": missing_requirements,
            "coverage_percentage": coverage_percentage,
            "status": status,
        }

    def generate_mission_suggestions(
        self,
        coverage_object_id: str,
        *,
        mission_id: str,
        priority: str = "high",
    ) -> list[dict[str, Any]]:
        evaluation = self.evaluate_and_record(coverage_object_id)
        suggestions: list[dict[str, Any]] = []
        if not evaluation["missing_crs_requirements"]:
            return suggestions

        missing_types = [req["reference_type"] for req in evaluation["missing_crs_requirements"]]
        coverage = self.coverage_store.get_coverage_object(coverage_object_id)
        objective = (
            f"Acquire authoritative sources for {coverage['title']} "
            f"missing CRS types: {', '.join(missing_types)}"
        )
        suggestion = self.coverage_store.create_mission_suggestion(
            mission_id=mission_id,
            coverage_object_id=coverage_object_id,
            missing_reference_types=missing_types,
            objective=objective,
            priority=priority,
            metadata={"evaluation": evaluation},
        )
        if self.acp_log_store is not None:
            emit_acp_events(
                [
                    prepare_coverage_mission_generated_event(
                        mission_id=mission_id,
                        coverage_object_id=coverage_object_id,
                        objective=objective,
                        missing_reference_types=missing_types,
                        suggestion_id=suggestion["suggestion_id"],
                    )
                ],
                log_store=self.acp_log_store,
            )
        suggestions.append(suggestion)
        return suggestions

    def _mission_id_for_coverage(self, coverage_object_id: str) -> str:
        if self.ledger is None:
            return "mission:system"
        for source_uuid in self.coverage_store.list_coverage_for_source_by_object(coverage_object_id):
            source = self.ledger.get_source(source_uuid)
            return source.get("mission_id") or source["mission"]
        return "mission:system"
