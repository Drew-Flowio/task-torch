import json
import tempfile
import unittest
from pathlib import Path

from internal_tools.ogm_milestone_001 import (
    CoverageStore,
    IntakeLedger,
    KnowledgeRepository,
    RawSourceVault,
    bridge_intake_to_repository,
)


class Milestone2BridgeTests(unittest.TestCase):
    def _setup(self, root: Path):
        sample = root / "guide.txt"
        sample.write_text("Trusted field guide content.\n", encoding="utf-8")

        ledger = IntakeLedger(root / "intake.db")
        vault = RawSourceVault(root / "vault", ledger)
        repository = KnowledgeRepository(root / "repository.db")
        coverage = CoverageStore(root / "repository.db")

        coverage.create_coverage_object(
            coverage_object_id="cov:ogm.pack.outdoor:species:trees:acer-rubrum",
            domain="outdoor",
            category="species",
            subcategory="trees",
            title="Red Maple coverage",
        )
        coverage.add_canonical_reference_requirement(
            coverage_object_id="cov:ogm.pack.outdoor:species:trees:acer-rubrum",
            reference_type="government_publication",
            minimum_authority="government",
        )

        source = vault.store_approved_source(
            sample,
            source="human-approved upload",
            license="internal_test",
            mission="mission:outdoor:trees-001",
            mission_id="mission:outdoor:trees-001",
            curator="curator-001",
            approval_status="approved",
            coverage_object_ids=["cov:ogm.pack.outdoor:species:trees:acer-rubrum"],
            curator_recommendation_id="rec:curator:2026-07-06:001",
            human_approval_id="approval:source-intake:2026-07-06:001",
            source_quality_score=0.92,
            canonical_reference_type="government_publication",
            actor="human:reviewer:001",
        )
        return ledger, vault, repository, coverage, source

    def test_vaulted_source_links_to_coverage_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger, _vault, _repo, coverage, source = self._setup(root)

            self.assertEqual(
                source["coverage_object_ids"],
                ["cov:ogm.pack.outdoor:species:trees:acer-rubrum"],
            )
            self.assertEqual(source["mission_id"], "mission:outdoor:trees-001")
            self.assertEqual(source["curator_recommendation_id"], "rec:curator:2026-07-06:001")
            self.assertEqual(source["human_approval_id"], "approval:source-intake:2026-07-06:001")
            self.assertEqual(source["source_quality_score"], 0.92)
            self.assertEqual(source["canonical_reference_type"], "government_publication")

            coverage.link_source_to_coverage(source["uuid"], source["coverage_object_ids"][0])
            self.assertEqual(
                coverage.list_coverage_for_source(source["uuid"]),
                ["cov:ogm.pack.outdoor:species:trees:acer-rubrum"],
            )
            self.assertEqual(len(ledger.list_sources(mission_id="mission:outdoor:trees-001")), 1)

    def test_source_revision_becomes_repository_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger, vault, repository, coverage, source = self._setup(root)
            acp_log = root / "acp.events.jsonl"

            result = bridge_intake_to_repository(
                ledger=ledger,
                repository=repository,
                source_uuid=source["uuid"],
                revision_uuid=source["revision"]["revision_uuid"],
                coverage_store=coverage,
                vault=vault,
                actor="human:reviewer:001",
                acp_log_path=acp_log,
            )

            evidence = result["evidence"]
            self.assertTrue(evidence["evidence_uuid"].startswith("ev:"))
            self.assertEqual(evidence["source_uuid"], source["uuid"])
            self.assertEqual(evidence["raw_revision_uuid"], source["revision"]["revision_uuid"])
            self.assertEqual(evidence["locator"]["type"], "raw_source")
            self.assertEqual(
                coverage.list_coverage_for_evidence(evidence["evidence_uuid"]),
                ["cov:ogm.pack.outdoor:species:trees:acer-rubrum"],
            )

            updated = ledger.get_source(source["uuid"])
            self.assertEqual(updated["processing_state"], "evidence_linked")

            acp_lines = acp_log.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(acp_lines), 2)
            event_types = {json.loads(line)["message_type"] for line in acp_lines}
            self.assertEqual(event_types, {"SourceAcquired", "EvidenceLinked"})

    def test_provenance_chain_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger, vault, repository, coverage, source = self._setup(root)

            result = bridge_intake_to_repository(
                ledger=ledger,
                repository=repository,
                source_uuid=source["uuid"],
                revision_uuid=source["revision"]["revision_uuid"],
                coverage_store=coverage,
                vault=vault,
            )
            provenance = result["provenance"]

            self.assertEqual(provenance["mission_id"], "mission:outdoor:trees-001")
            self.assertEqual(provenance["source_uuid"], source["uuid"])
            self.assertEqual(provenance["raw_revision_uuid"], source["revision"]["revision_uuid"])
            self.assertEqual(provenance["human_approval_id"], "approval:source-intake:2026-07-06:001")
            self.assertEqual(provenance["checksum"], source["checksum"])
            self.assertEqual(provenance["coverage_object_ids"], source["coverage_object_ids"])

            obj = repository.create_knowledge_object(
                canonical_key="outdoor:species:acer-rubrum",
                category="Species",
                title="Red Maple",
                summary="Red Maple species profile.",
                body={"format": "plain", "value": "Acer rubrum"},
                provenance=provenance,
                confidence={"overall": 0.9},
                evidence_refs=[result["evidence"]["evidence_uuid"]],
            )
            self.assertEqual(obj["provenance"]["source_uuid"], source["uuid"])
            self.assertEqual(obj["evidence_refs"], [result["evidence"]["evidence_uuid"]])


class Milestone2ReviewTests(unittest.TestCase):
    def _object(self, repo: KnowledgeRepository, source_uuid: str, evidence_uuid: str):
        return repo.create_knowledge_object(
            canonical_key="outdoor:procedure:boil-water",
            category="Procedure",
            title="Boil water",
            summary="Bring water to a rolling boil.",
            body={"format": "plain", "value": "Bring water to a rolling boil."},
            provenance={"source_uuid": source_uuid},
            confidence={"overall": 0.9},
            evidence_refs=[evidence_uuid],
        )

    def test_review_state_transitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = IntakeLedger(root / "intake.db")
            repo = KnowledgeRepository(root / "repository.db")
            sample = root / "source.txt"
            sample.write_text("Step 1\n", encoding="utf-8")
            vault = RawSourceVault(root / "vault", ledger)
            source = vault.store_approved_source(
                sample,
                source="human upload",
                license="internal_test",
                mission="mission:test",
                curator="curator-001",
                approval_status="approved",
            )
            bridged = bridge_intake_to_repository(
                ledger=ledger,
                repository=repo,
                source_uuid=source["uuid"],
                revision_uuid=source["revision"]["revision_uuid"],
                vault=vault,
            )
            obj = self._object(repo, source["uuid"], bridged["evidence"]["evidence_uuid"])

            obj = repo.transition_object_status(obj["object_uuid"], "needs_review", actor="human:reviewer:001")
            self.assertEqual(obj["status"], "needs_review")
            obj = repo.transition_object_status(obj["object_uuid"], "approved", actor="human:reviewer:001", reason="reviewed")
            self.assertEqual(obj["status"], "approved")

            audit_actions = [event["action"] for event in repo.list_audit_events(obj["object_uuid"])]
            self.assertIn("knowledge_object_status_changed", audit_actions)

    def test_rejected_object_requires_re_review_before_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = IntakeLedger(root / "intake.db")
            repo = KnowledgeRepository(root / "repository.db")
            sample = root / "source.txt"
            sample.write_text("Step 1\n", encoding="utf-8")
            vault = RawSourceVault(root / "vault", ledger)
            source = vault.store_approved_source(
                sample,
                source="human upload",
                license="internal_test",
                mission="mission:test",
                curator="curator-001",
                approval_status="approved",
            )
            bridged = bridge_intake_to_repository(
                ledger=ledger,
                repository=repo,
                source_uuid=source["uuid"],
                revision_uuid=source["revision"]["revision_uuid"],
                vault=vault,
            )
            obj = self._object(repo, source["uuid"], bridged["evidence"]["evidence_uuid"])
            obj = repo.transition_object_status(obj["object_uuid"], "rejected", actor="human:reviewer:001", reason="insufficient evidence")

            with self.assertRaises(ValueError):
                repo.transition_object_status(obj["object_uuid"], "approved", actor="human:reviewer:001")

            obj = repo.transition_object_status(obj["object_uuid"], "needs_review", actor="human:reviewer:001", reason="re-review requested")
            obj = repo.transition_object_status(obj["object_uuid"], "approved", actor="human:reviewer:001", reason="approved after re-review")
            self.assertEqual(obj["status"], "approved")

            status_events = [
                event
                for event in repo.list_audit_events(obj["object_uuid"])
                if event["action"] == "knowledge_object_status_changed"
            ]
            self.assertGreaterEqual(len(status_events), 3)
            self.assertEqual(status_events[-1]["details"]["to_status"], "approved")


if __name__ == "__main__":
    unittest.main()
