import tempfile
import unittest
from pathlib import Path

from internal_tools.ogm_acp import ACPLogStore
from internal_tools.ogm_milestone_001 import (
    CandidateIntakeQueue,
    CoverageStore,
    Curator001,
    IntakeLedger,
    KnowledgeRepository,
    OperationalRecords,
    RawSourceVault,
    approved_candidate_to_repository_evidence,
)


class CandidateReviewWorkflowTests(unittest.TestCase):
    MISSION_ID = "mission:curator-001:north-american-outdoor:trees"
    COVERAGE_ID = "cov:ogm.pack.outdoor:species:trees:acer-rubrum"

    def _setup(self, root: Path):
        records = OperationalRecords(root / "intake.db")
        queue = CandidateIntakeQueue(root / "intake.db", records=records)
        coverage = CoverageStore(root / "repository.db")
        ledger = IntakeLedger(root / "intake.db")
        vault = RawSourceVault(root / "vault", ledger)
        repository = KnowledgeRepository(root / "repository.db")
        acp_log = ACPLogStore(root / "acp.jsonl")

        records.create_mission(
            mission_id=self.MISSION_ID,
            title="Curator-001 North American Outdoor Trees",
            target_pack_id=Curator001.TARGET_PACK_ID,
            metadata={"coverage_object_ids": [self.COVERAGE_ID]},
        )
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
        curator = Curator001(records=records, coverage_store=coverage)
        return records, queue, coverage, ledger, vault, repository, acp_log, curator

    def _submit_candidate(self, queue: CandidateIntakeQueue, root: Path, **overrides):
        source_file = root / f"{overrides.get('candidate_id', 'cand-red-maple').replace(':', '-')}.txt"
        source_file.write_text("approved red maple source\n", encoding="utf-8")
        data = {
            "candidate_id": "cand:review:red-maple",
            "title": "Red Maple Species Profile",
            "publisher": "United States Forest Service",
            "local_file_path": source_file,
            "source_type": "government",
            "submitted_by": "human:submitter:001",
            "mission_id": self.MISSION_ID,
            "coverage_object_id": self.COVERAGE_ID,
            "proposed_canonical_reference_type": "government_publication",
            "notes": "Candidate submitted manually for review.",
            "authority_score": 0.95,
            "authority_reason": "Government forestry publisher.",
        }
        data.update(overrides)
        return queue.submit_candidate(**data)

    def _recommend_and_approve(self, records, queue, curator, candidate_id: str):
        recommendations = curator.recommend_from_queue(
            self.MISSION_ID,
            candidate_queue=queue,
            candidate_ids=[candidate_id],
        )
        recommendation = recommendations[0]
        approval = records.create_human_approval(
            approval_id=f"approval:{candidate_id.replace(':', '-')}",
            mission_id=self.MISSION_ID,
            recommendation_id=recommendation["recommendation_id"],
            approver_id="human:reviewer:001",
            decision="approved",
            target_type="source_intake",
        )
        queue.update_candidate_review(
            candidate_id,
            status="approved_for_intake",
            actor="human:reviewer:001",
            reason="approved by human reviewer",
        )
        return recommendation, approval

    def test_review_history_is_append_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _records, queue, _coverage, _ledger, _vault, _repo, _acp, _curator = self._setup(root)
            candidate = self._submit_candidate(queue, root)
            first_events = queue.list_review_events(candidate["candidate_id"])

            queue.update_candidate_review(
                candidate["candidate_id"],
                status="under_review",
                actor="human:reviewer:001",
                reason="review started",
            )
            queue.update_candidate_review(
                candidate["candidate_id"],
                status="rejected",
                actor="human:reviewer:001",
                reason="test rejection",
            )
            events = queue.list_review_events(candidate["candidate_id"])

            self.assertEqual(len(first_events), 1)
            self.assertEqual([event["to_status"] for event in events], ["submitted", "under_review", "rejected"])
            self.assertEqual(len({event["event_id"] for event in events}), 3)

    def test_reviewer_assignment_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _records, queue, _coverage, _ledger, _vault, _repo, _acp, _curator = self._setup(root)
            candidate = self._submit_candidate(queue, root)

            updated = queue.assign_reviewer(
                candidate["candidate_id"],
                assigned_reviewer="human:reviewer:001",
                review_due_at="2026-07-10T00:00:00Z",
                review_priority="high",
                actor="human:lead:001",
            )

            self.assertEqual(updated["assigned_reviewer"], "human:reviewer:001")
            self.assertEqual(updated["review_due_at"], "2026-07-10T00:00:00Z")
            self.assertEqual(updated["review_priority"], "high")
            self.assertEqual(queue.list_review_events(candidate["candidate_id"])[-1]["reason"], "reviewer assigned")

    def test_license_evidence_is_stored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _records, queue, _coverage, _ledger, _vault, _repo, _acp, _curator = self._setup(root)
            candidate = self._submit_candidate(queue, root)

            updated = queue.attach_license_evidence(
                candidate["candidate_id"],
                license_status="public_domain_or_government_work",
                license_source_url="https://example.gov/license",
                license_text_excerpt="Works of this agency are public domain.",
                license_checked_by="human:reviewer:001",
                license_notes="Local fixture for license evidence.",
            )

            self.assertEqual(updated["license_status"], "public_domain_or_government_work")
            self.assertEqual(updated["license_source_url"], "https://example.gov/license")
            self.assertEqual(updated["license_checked_by"], "human:reviewer:001")
            self.assertIn("public domain", updated["license_text_excerpt"])

    def test_approved_candidate_moves_to_vault_and_repository_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records, queue, coverage, ledger, vault, repository, acp_log, curator = self._setup(root)
            candidate = self._submit_candidate(queue, root)
            queue.attach_license_evidence(
                candidate["candidate_id"],
                license_status="public_domain_or_government_work",
                license_source_url="https://example.gov/license",
                license_text_excerpt="Government work.",
                license_checked_by="human:reviewer:001",
            )
            self._recommend_and_approve(records, queue, curator, candidate["candidate_id"])

            result = approved_candidate_to_repository_evidence(
                candidate_queue=queue,
                candidate_id=candidate["candidate_id"],
                ledger=ledger,
                vault=vault,
                repository=repository,
                coverage_store=coverage,
                actor="human:reviewer:001",
                strict_license_review=True,
                acp_log_store=acp_log,
            )

            self.assertTrue(result["source_uuid"].startswith("src:"))
            self.assertTrue(result["revision_uuid"].startswith("rev:"))
            self.assertTrue(result["evidence_uuid"].startswith("ev:"))
            self.assertEqual(coverage.list_coverage_for_evidence(result["evidence_uuid"]), [self.COVERAGE_ID])
            events = queue.list_review_events(candidate["candidate_id"])
            self.assertEqual(events[-3]["to_status"], "sent_to_vault")
            self.assertEqual(events[-2]["to_status"], "vaulted")
            self.assertEqual(events[-1]["to_status"], "bridged_to_repository")

            event_types = {message.message_type for message in acp_log.replay(mission_id=self.MISSION_ID)}
            self.assertIn("SourceAcquired", event_types)
            self.assertIn("EvidenceLinked", event_types)

    def test_rejected_candidate_cannot_be_vaulted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records, queue, coverage, ledger, vault, repository, _acp, curator = self._setup(root)
            candidate = self._submit_candidate(queue, root)
            self._recommend_and_approve(records, queue, curator, candidate["candidate_id"])
            queue.update_candidate_review(
                candidate["candidate_id"],
                status="rejected",
                actor="human:reviewer:001",
                reason="rejected after approval",
            )

            with self.assertRaises(PermissionError):
                approved_candidate_to_repository_evidence(
                    candidate_queue=queue,
                    candidate_id=candidate["candidate_id"],
                    ledger=ledger,
                    vault=vault,
                    repository=repository,
                    coverage_store=coverage,
                )

    def test_url_only_candidate_cannot_be_vaulted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records, queue, coverage, ledger, vault, repository, _acp, curator = self._setup(root)
            candidate = self._submit_candidate(
                queue,
                root,
                candidate_id="cand:url-only",
                local_file_path=None,
                url="https://example.gov/red-maple",
            )
            self._recommend_and_approve(records, queue, curator, candidate["candidate_id"])

            with self.assertRaises(FileNotFoundError):
                approved_candidate_to_repository_evidence(
                    candidate_queue=queue,
                    candidate_id=candidate["candidate_id"],
                    ledger=ledger,
                    vault=vault,
                    repository=repository,
                    coverage_store=coverage,
                )

    def test_missing_human_approval_blocks_orchestration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _records, queue, coverage, ledger, vault, repository, _acp, _curator = self._setup(root)
            candidate = self._submit_candidate(queue, root)
            queue.update_candidate_review(
                candidate["candidate_id"],
                status="approved_for_intake",
                actor="human:reviewer:001",
                reason="status set without approval",
            )

            with self.assertRaises(PermissionError):
                approved_candidate_to_repository_evidence(
                    candidate_queue=queue,
                    candidate_id=candidate["candidate_id"],
                    ledger=ledger,
                    vault=vault,
                    repository=repository,
                    coverage_store=coverage,
                )


if __name__ == "__main__":
    unittest.main()
