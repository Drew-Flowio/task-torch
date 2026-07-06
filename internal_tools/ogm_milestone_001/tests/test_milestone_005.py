import tempfile
import unittest
from pathlib import Path

from internal_tools.ogm_milestone_001 import (
    CandidateIntakeQueue,
    CoverageStore,
    Curator001,
    OperationalRecords,
)


class CandidateIntakeQueueTests(unittest.TestCase):
    MISSION_ID = "mission:curator-001:north-american-outdoor:trees"
    COVERAGE_ID = "cov:ogm.pack.outdoor:species:trees:acer-rubrum"

    def _setup(self, root: Path):
        records = OperationalRecords(root / "intake.db")
        coverage = CoverageStore(root / "repository.db")
        queue = CandidateIntakeQueue(root / "intake.db", records=records)
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
        return records, coverage, queue, curator

    def _submit_candidate(self, queue: CandidateIntakeQueue, **overrides):
        data = {
            "candidate_id": "cand:usfs-red-maple",
            "title": "Red Maple Species Profile",
            "publisher": "United States Forest Service",
            "url": "https://www.example.gov/usfs/red-maple/?b=2&a=1",
            "source_type": "government",
            "submitted_by": "human:submitter:001",
            "mission_id": self.MISSION_ID,
            "coverage_object_id": self.COVERAGE_ID,
            "proposed_canonical_reference_type": "government_publication",
            "notes": "Candidate submitted manually for Curator-001 review.",
            "license_status": "public_domain_or_government_work",
            "license_notes": "Likely US government work; confirm before intake.",
            "authority_score": 0.95,
            "authority_reason": "Government forestry publisher.",
            "risk_notes": "Example URL used in local test fixture.",
            "reviewer_notes": "Looks appropriate for CRS review.",
        }
        data.update(overrides)
        return queue.submit_candidate(**data)

    def test_manual_candidate_can_be_submitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            _records, _coverage, queue, _curator = self._setup(Path(tmp))
            candidate = self._submit_candidate(queue)

            self.assertEqual(candidate["candidate_id"], "cand:usfs-red-maple")
            self.assertEqual(candidate["status"], "submitted")
            self.assertEqual(candidate["mission_id"], self.MISSION_ID)
            self.assertEqual(candidate["coverage_object_id"], self.COVERAGE_ID)
            self.assertEqual(candidate["proposed_canonical_reference_type"], "government_publication")
            self.assertEqual(candidate["authority_score"], 0.95)

    def test_duplicate_url_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _records, _coverage, queue, _curator = self._setup(Path(tmp))
            first = self._submit_candidate(queue)
            duplicate = self._submit_candidate(
                queue,
                candidate_id="cand:usfs-red-maple-duplicate",
                url="https://example.gov/usfs/red-maple?a=1&b=2",
            )

            self.assertEqual(duplicate["duplicate_of_candidate_id"], first["candidate_id"])
            reasons = duplicate["metadata"]["duplicate_candidates"][0]["duplicate_reasons"]
            self.assertIn("url", reasons)

    def test_local_file_checksum_duplicate_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _records, _coverage, queue, _curator = self._setup(root)
            first_file = root / "red-maple-a.txt"
            second_file = root / "red-maple-b.txt"
            first_file.write_text("same source content\n", encoding="utf-8")
            second_file.write_text("same source content\n", encoding="utf-8")

            first = self._submit_candidate(
                queue,
                candidate_id="cand:file-a",
                url=None,
                local_file_path=first_file,
            )
            duplicate = self._submit_candidate(
                queue,
                candidate_id="cand:file-b",
                title="Different Red Maple File Title",
                url=None,
                local_file_path=second_file,
            )

            self.assertEqual(duplicate["duplicate_of_candidate_id"], first["candidate_id"])
            reasons = duplicate["metadata"]["duplicate_candidates"][0]["duplicate_reasons"]
            self.assertIn("file_checksum", reasons)

    def test_curator_can_evaluate_candidate_from_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            _records, _coverage, queue, curator = self._setup(Path(tmp))
            candidate = self._submit_candidate(queue)

            recommendations = curator.recommend_from_queue(
                self.MISSION_ID,
                candidate_queue=queue,
                candidate_ids=[candidate["candidate_id"]],
            )

            self.assertEqual(len(recommendations), 1)
            recommendation = recommendations[0]
            updated = queue.get_candidate(candidate["candidate_id"])
            self.assertEqual(updated["status"], "recommended")
            self.assertEqual(updated["curator_recommendation_id"], recommendation["recommendation_id"])
            self.assertEqual(recommendation["metadata"]["candidate_id"], candidate["candidate_id"])
            self.assertEqual(recommendation["metadata"]["queued_candidate"], True)

    def test_rejected_candidate_cannot_enter_intake(self):
        with tempfile.TemporaryDirectory() as tmp:
            _records, _coverage, queue, curator = self._setup(Path(tmp))
            candidate = self._submit_candidate(
                queue,
                candidate_id="cand:seo-red-maple",
                publisher="Example SEO Farm",
                source_type="seo_content",
                authority_score=0.2,
            )

            recommendations = curator.recommend_from_queue(
                self.MISSION_ID,
                candidate_queue=queue,
                candidate_ids=[candidate["candidate_id"]],
            )

            self.assertEqual(recommendations, [])
            rejected = queue.get_candidate(candidate["candidate_id"])
            self.assertEqual(rejected["status"], "rejected")
            with self.assertRaises(PermissionError):
                queue.prepare_for_vault_intake(candidate["candidate_id"])

    def test_approved_candidate_can_be_prepared_for_vault_intake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records, _coverage, queue, curator = self._setup(root)
            source_file = root / "red-maple-approved.txt"
            source_file.write_text("approved source content\n", encoding="utf-8")
            candidate = self._submit_candidate(
                queue,
                candidate_id="cand:file-approved",
                url=None,
                local_file_path=source_file,
            )
            recommendations = curator.recommend_from_queue(
                self.MISSION_ID,
                candidate_queue=queue,
                candidate_ids=[candidate["candidate_id"]],
            )
            recommendation = recommendations[0]

            records.create_human_approval(
                approval_id="approval:candidate:file-approved",
                mission_id=self.MISSION_ID,
                recommendation_id=recommendation["recommendation_id"],
                approver_id="human:reviewer:001",
                decision="approved",
                target_type="source_intake",
            )
            queue.update_candidate_review(candidate["candidate_id"], status="approved_for_intake")

            intake_payload = queue.prepare_for_vault_intake(candidate["candidate_id"])
            self.assertEqual(intake_payload["file_path"], str(source_file))
            self.assertEqual(intake_payload["mission_id"], self.MISSION_ID)
            self.assertEqual(intake_payload["coverage_object_ids"], [self.COVERAGE_ID])
            self.assertEqual(intake_payload["curator_recommendation_id"], recommendation["recommendation_id"])
            self.assertEqual(intake_payload["human_approval_id"], "approval:candidate:file-approved")
            self.assertEqual(intake_payload["canonical_reference_type"], "government_publication")


if __name__ == "__main__":
    unittest.main()
