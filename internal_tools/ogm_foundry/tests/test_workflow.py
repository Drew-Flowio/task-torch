import csv
import tempfile
import unittest
from pathlib import Path

from internal_tools.ogm_foundry.approve_workflow import approve_candidate
from internal_tools.ogm_foundry.bootstrap_workspace import bootstrap_workspace
from internal_tools.ogm_foundry.config import FoundryConfig
from internal_tools.ogm_foundry.curator_workflow import evaluate_candidates
from internal_tools.ogm_foundry.data import FoundryDataReader
from internal_tools.ogm_foundry.import_candidates import import_candidates
from internal_tools.ogm_foundry.intake_workflow import intake_approved_candidate
from internal_tools.ogm_foundry.runtime import load_services
from internal_tools.ogm_foundry.workspace_spec import CANDIDATE_TEMPLATE_FIELDS, WORKSPACE_TOPICS


class FoundryWorkflowTests(unittest.TestCase):
    def _config(self, root: Path) -> FoundryConfig:
        return FoundryConfig(
            data_root=root,
            intake_db=root / "intake.db",
            repository_db=root / "repository.db",
            vault_root=root / "vault",
            host="127.0.0.1",
            port=8790,
        )

    def _write_csv(self, path: Path, row: dict[str, str]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(CANDIDATE_TEMPLATE_FIELDS))
            writer.writeheader()
            writer.writerow(row)

    def _bootstrap_and_import(self, root: Path, *, local_file: Path | None = None, url: str = ""):
        config = self._config(root)
        bootstrap_workspace(config)
        topic = WORKSPACE_TOPICS[0]
        if local_file is None:
            local_file = root / "usfs-trees.txt"
            local_file.write_text("Red maple government forestry reference.\n", encoding="utf-8")
        csv_path = root / "candidates.csv"
        self._write_csv(
            csv_path,
            {
                "title": "USFS Red Maple Guide",
                "publisher": "United States Forest Service",
                "url": url,
                "local_file_path": str(local_file) if not url else "",
                "source_type": "government",
                "mission_id": topic.mission_id,
                "coverage_object_id": topic.coverage_object_id,
                "proposed_canonical_reference_type": "government_publication",
                "submitted_by": "human:researcher:001",
                "license_status": "public_domain_or_government_work",
                "license_notes": "To be verified manually.",
                "authority_score": "0.95",
                "authority_reason": "Government forestry publisher.",
                "risk_notes": "",
                "notes": "Real candidate for workflow test.",
            },
        )
        import_result = import_candidates(csv_path, config)
        self.assertEqual(import_result["candidates_created"], 1)
        services = load_services(config)
        candidate = services.queue.list_candidates(status="submitted")[0]
        return config, services, candidate, topic

    def test_imported_candidate_can_be_evaluated_by_curator(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, services, candidate, _topic = self._bootstrap_and_import(Path(tmp))
            result = evaluate_candidates(services, candidate_id=candidate["candidate_id"])
            self.assertEqual(result["evaluated"], 1)
            self.assertEqual(len(result["recommended"]), 1)
            updated = services.queue.get_candidate(candidate["candidate_id"])
            self.assertEqual(updated["status"], "recommended")
            self.assertTrue(updated["curator_recommendation_id"])

    def test_recommended_candidate_can_be_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, services, candidate, _topic = self._bootstrap_and_import(Path(tmp))
            evaluate_candidates(services, candidate_id=candidate["candidate_id"])
            approval = approve_candidate(
                services,
                candidate["candidate_id"],
                actor="Andrew",
                notes="Approved as authoritative government forestry reference",
            )
            updated = services.queue.get_candidate(candidate["candidate_id"])
            self.assertEqual(updated["status"], "approved_for_intake")
            self.assertEqual(approval["approver_id"], "Andrew")
            self.assertEqual(len(services.records.list_human_approvals()), 1)

    def test_candidate_cannot_be_approved_without_recommendation(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, services, candidate, _topic = self._bootstrap_and_import(Path(tmp))
            with self.assertRaises(PermissionError):
                approve_candidate(
                    services,
                    candidate["candidate_id"],
                    actor="Andrew",
                    notes="Should fail",
                )

    def test_crs_evaluation_updates_coverage_after_evidence_linked(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, services, candidate, topic = self._bootstrap_and_import(Path(tmp))
            before = services.coverage.get_coverage_object(topic.coverage_object_id)
            self.assertEqual(before["coverage_percentage"], 0.0)
            evaluate_candidates(services, candidate_id=candidate["candidate_id"])
            approve_candidate(
                services,
                candidate["candidate_id"],
                actor="Andrew",
                notes="Approved for intake",
            )
            intake_approved_candidate(services, candidate["candidate_id"], actor="Andrew")
            after = services.coverage.get_coverage_object(topic.coverage_object_id)
            self.assertGreater(after["coverage_percentage"], before["coverage_percentage"])

    def test_approved_candidate_with_local_file_is_vaulted_and_bridged(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, services, candidate, topic = self._bootstrap_and_import(Path(tmp))
            evaluate_candidates(services, candidate_id=candidate["candidate_id"])
            approve_candidate(
                services,
                candidate["candidate_id"],
                actor="Andrew",
                notes="Approved for intake",
            )
            result = intake_approved_candidate(services, candidate["candidate_id"], actor="Andrew")
            self.assertTrue(result["source_uuid"].startswith("src:"))
            self.assertTrue(result["revision_uuid"].startswith("rev:"))
            self.assertTrue(result["evidence_uuid"].startswith("ev:"))
            self.assertGreater(result["coverage_percentage"], 0.0)
            self.assertEqual(result["crs_evaluation"]["satisfied_crs_count"], 1)
            updated = services.queue.get_candidate(candidate["candidate_id"])
            self.assertEqual(updated["status"], "bridged_to_repository")
            self.assertEqual(
                services.coverage.list_coverage_for_evidence(result["evidence_uuid"]),
                [topic.coverage_object_id],
            )

    def test_url_only_candidate_cannot_be_vaulted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, services, candidate, _topic = self._bootstrap_and_import(
                root,
                local_file=None,
                url="https://example.gov/usfs/trees",
            )
            evaluate_candidates(services, candidate_id=candidate["candidate_id"])
            approve_candidate(
                services,
                candidate["candidate_id"],
                actor="Andrew",
                notes="Approved pending file acquisition",
            )
            with self.assertRaises(FileNotFoundError):
                intake_approved_candidate(services, candidate["candidate_id"], actor="Andrew")

    def test_rejected_candidate_cannot_be_approved_or_intaken(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config, services, candidate, _topic = self._bootstrap_and_import(root)
            services.queue.update_candidate_review(
                candidate["candidate_id"],
                status="rejected",
                actor="human:reviewer:001",
                reason="test rejection",
            )
            with self.assertRaises(PermissionError):
                approve_candidate(
                    services,
                    candidate["candidate_id"],
                    actor="Andrew",
                    notes="Should fail",
                )
            with self.assertRaises(PermissionError):
                intake_approved_candidate(services, candidate["candidate_id"], actor="Andrew")

    def test_dashboard_summary_reflects_workflow_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, services, candidate, _topic = self._bootstrap_and_import(Path(tmp))
            evaluate_candidates(services, candidate_id=candidate["candidate_id"])
            approve_candidate(
                services,
                candidate["candidate_id"],
                actor="Andrew",
                notes="Approved for intake",
            )
            intake_approved_candidate(services, candidate["candidate_id"], actor="Andrew")
            summary = FoundryDataReader(config).dashboard_summary()
            self.assertEqual(summary["candidate_queue"]["recommended"], 0)
            self.assertEqual(summary["vault"]["sources"], 1)
            self.assertEqual(summary["repository"]["evidence"], 1)
            self.assertGreater(summary["coverage"]["average_coverage_percentage"], 0.0)
            self.assertEqual(summary["candidates"]["count"], 1)


if __name__ == "__main__":
    unittest.main()
