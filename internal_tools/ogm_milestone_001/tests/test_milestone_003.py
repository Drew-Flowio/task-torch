import json
import tempfile
import unittest
from pathlib import Path

from internal_tools.ogm_acp import ACPLogStore
from internal_tools.ogm_milestone_001 import (
    CRSEvaluator,
    CoverageStore,
    IntakeLedger,
    KnowledgeRepository,
    OperationalRecords,
    RawSourceVault,
    bridge_intake_to_repository,
)


class Milestone3CRSTests(unittest.TestCase):
    COVERAGE_ID = "cov:ogm.pack.outdoor:species:trees:acer-rubrum"
    MISSION_ID = "mission:outdoor:trees-001"

    def _setup(self, root: Path):
        sample = root / "guide.txt"
        sample.write_text("Red maple field guide.\n", encoding="utf-8")

        records = OperationalRecords(root / "intake.db")
        records.create_mission(
            mission_id=self.MISSION_ID,
            title="Improve tree coverage",
            target_pack_id="ogm.pack.north-american-outdoor",
        )
        records.create_curator_recommendation(
            recommendation_id="rec:curator:2026-07-06:001",
            mission_id=self.MISSION_ID,
            curator_id="curator-001",
            source_label="USFS tree guide",
        )
        records.create_human_approval(
            approval_id="approval:source-intake:2026-07-06:001",
            mission_id=self.MISSION_ID,
            recommendation_id="rec:curator:2026-07-06:001",
            approver_id="human:reviewer:001",
            decision="approved",
            target_type="source_intake",
        )

        ledger = IntakeLedger(root / "intake.db")
        vault = RawSourceVault(root / "vault", ledger)
        repository = KnowledgeRepository(root / "repository.db")
        coverage = CoverageStore(root / "repository.db")
        acp_log = ACPLogStore(root / "acp.jsonl")

        coverage.create_coverage_object(
            coverage_object_id=self.COVERAGE_ID,
            domain="outdoor",
            category="species",
            subcategory="trees",
            title="Red Maple",
        )
        coverage.add_canonical_reference_requirement(
            coverage_object_id=self.COVERAGE_ID,
            reference_type="government_publication",
            minimum_authority="government",
        )
        coverage.add_canonical_reference_requirement(
            coverage_object_id=self.COVERAGE_ID,
            reference_type="professional_field_guide",
            minimum_authority="professional",
        )

        source = vault.store_approved_source(
            sample,
            source="human-approved upload",
            license="internal_test",
            mission=self.MISSION_ID,
            mission_id=self.MISSION_ID,
            curator="curator-001",
            approval_status="approved",
            coverage_object_ids=[self.COVERAGE_ID],
            curator_recommendation_id="rec:curator:2026-07-06:001",
            human_approval_id="approval:source-intake:2026-07-06:001",
            source_quality_score=0.92,
            canonical_reference_type="government_publication",
        )

        return records, ledger, vault, repository, coverage, acp_log, source

    def test_crs_requirements_can_be_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            _records, _ledger, _vault, _repo, coverage, _acp, _source = self._setup(Path(tmp))
            requirements = coverage.list_canonical_reference_requirements(self.COVERAGE_ID)
            self.assertEqual(len(requirements), 2)
            self.assertEqual(requirements[0]["reference_type"], "government_publication")

    def test_linked_evidence_satisfies_crs_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _records, ledger, vault, repository, coverage, acp_log, source = self._setup(root)
            bridge_intake_to_repository(
                ledger=ledger,
                repository=repository,
                source_uuid=source["uuid"],
                revision_uuid=source["revision"]["revision_uuid"],
                coverage_store=coverage,
                vault=vault,
                acp_log_store=acp_log,
            )

            evaluator = CRSEvaluator(coverage, ledger=ledger, repository=repository, acp_log_store=acp_log)
            evaluation = evaluator.evaluate_and_record(self.COVERAGE_ID)

            self.assertEqual(evaluation["required_crs_count"], 2)
            self.assertEqual(evaluation["satisfied_crs_count"], 1)
            self.assertEqual(evaluation["coverage_percentage"], 0.5)
            self.assertEqual(evaluation["status"], "partial")
            self.assertEqual(len(evaluation["missing_crs_requirements"]), 1)
            self.assertEqual(
                evaluation["missing_crs_requirements"][0]["reference_type"],
                "professional_field_guide",
            )

    def test_missing_crs_requirements_generate_mission_suggestions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _records, ledger, vault, repository, coverage, acp_log, source = self._setup(root)
            bridge_intake_to_repository(
                ledger=ledger,
                repository=repository,
                source_uuid=source["uuid"],
                revision_uuid=source["revision"]["revision_uuid"],
                coverage_store=coverage,
                vault=vault,
                acp_log_store=acp_log,
            )

            evaluator = CRSEvaluator(coverage, ledger=ledger, repository=repository, acp_log_store=acp_log)
            suggestions = evaluator.generate_mission_suggestions(
                self.COVERAGE_ID,
                mission_id=self.MISSION_ID,
            )

            self.assertEqual(len(suggestions), 1)
            self.assertIn("professional_field_guide", suggestions[0]["missing_reference_types"])
            self.assertEqual(suggestions[0]["status"], "suggested")

            stored = coverage.list_mission_suggestions(coverage_object_id=self.COVERAGE_ID)
            self.assertEqual(len(stored), 1)

            event_types = {msg.message_type for msg in acp_log.replay(mission_id=self.MISSION_ID)}
            self.assertIn("CoverageMissionGenerated", event_types)
            self.assertIn("CRSRequirementSatisfied", event_types)
            self.assertIn("CRSRequirementMissing", event_types)

    def test_human_approval_is_linked_to_source_intake(self):
        with tempfile.TemporaryDirectory() as tmp:
            records, _ledger, _vault, _repo, _coverage, _acp, source = self._setup(Path(tmp))
            approval = records.get_human_approval("approval:source-intake:2026-07-06:001")
            self.assertEqual(source["human_approval_id"], approval["approval_id"])
            self.assertEqual(approval["decision"], "approved")
            self.assertEqual(approval["mission_id"], self.MISSION_ID)

    def test_repository_object_created_event_is_emitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _records, ledger, vault, repository, coverage, acp_log, source = self._setup(root)
            repository.acp_log_store = acp_log
            bridged = bridge_intake_to_repository(
                ledger=ledger,
                repository=repository,
                source_uuid=source["uuid"],
                revision_uuid=source["revision"]["revision_uuid"],
                coverage_store=coverage,
                vault=vault,
                acp_log_store=acp_log,
            )
            repository.create_knowledge_object(
                canonical_key="outdoor:species:acer-rubrum",
                category="Species",
                title="Red Maple",
                summary="Red Maple species profile.",
                body={"format": "plain", "value": "Acer rubrum"},
                provenance=bridged["provenance"],
                confidence={"overall": 0.9},
                evidence_refs=[bridged["evidence"]["evidence_uuid"]],
            )

            event_types = {msg.message_type for msg in acp_log.replay(mission_id=self.MISSION_ID)}
            self.assertIn("RepositoryObjectCreated", event_types)


if __name__ == "__main__":
    unittest.main()
