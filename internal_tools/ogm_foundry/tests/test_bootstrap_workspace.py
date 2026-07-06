import csv
import json
import tempfile
import unittest
from pathlib import Path

from internal_tools.ogm_foundry.bootstrap_workspace import bootstrap_workspace, workspace_exists
from internal_tools.ogm_foundry.config import FoundryConfig
from internal_tools.ogm_foundry.data import FoundryDataReader
from internal_tools.ogm_foundry.import_candidates import import_candidates
from internal_tools.ogm_foundry.workspace_spec import (
    CANDIDATE_TEMPLATE_FIELDS,
    PACK_ID,
    WORKSPACE_TOPICS,
)
from internal_tools.ogm_milestone_001 import CandidateIntakeQueue, CoverageStore, OperationalRecords


class BootstrapWorkspaceTests(unittest.TestCase):
    def _config(self, root: Path) -> FoundryConfig:
        return FoundryConfig(
            data_root=root,
            intake_db=root / "intake.db",
            repository_db=root / "repository.db",
            vault_root=root / "vault",
            host="127.0.0.1",
            port=8790,
        )

    def test_bootstrap_creates_missions_coverage_and_crs(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            result = bootstrap_workspace(config)

            self.assertEqual(len(result["created_missions"]), len(WORKSPACE_TOPICS))
            self.assertEqual(len(result["created_coverage_objects"]), len(WORKSPACE_TOPICS))
            self.assertGreater(len(result["created_crs_requirements"]), 0)

            records = OperationalRecords(config.intake_db)
            coverage = CoverageStore(config.repository_db)
            missions = records.list_missions()
            self.assertEqual(len(missions), len(WORKSPACE_TOPICS))
            self.assertTrue(all(mission["target_pack_id"] == PACK_ID for mission in missions))

            coverage_objects = coverage.list_coverage_objects()
            self.assertEqual(len(coverage_objects), len(WORKSPACE_TOPICS))
            for topic in WORKSPACE_TOPICS:
                requirements = coverage.list_canonical_reference_requirements(topic.coverage_object_id)
                self.assertEqual(len(requirements), len(topic.crs_requirements))

            summary = FoundryDataReader(config).dashboard_summary()
            self.assertEqual(summary["missions"]["total"], len(WORKSPACE_TOPICS))
            self.assertEqual(summary["coverage"]["total"], len(WORKSPACE_TOPICS))
            self.assertGreater(summary["crs_requirements"]["total_requirements"], 0)
            self.assertEqual(summary["repository"]["knowledge_objects"], 0)
            self.assertEqual(summary["vault"]["sources"], 0)
            self.assertEqual(summary["candidate_queue"]["total"], 0)

    def test_bootstrap_refuses_to_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))
            bootstrap_workspace(config)
            self.assertTrue(workspace_exists(config))
            with self.assertRaises(RuntimeError):
                bootstrap_workspace(config)

    def test_candidate_template_exists(self):
        template = Path(__file__).resolve().parents[1] / "templates" / "candidates.csv"
        self.assertTrue(template.is_file())
        with template.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, list(CANDIDATE_TEMPLATE_FIELDS))


class ImportCandidatesTests(unittest.TestCase):
    def _config(self, root: Path) -> FoundryConfig:
        return FoundryConfig(
            data_root=root,
            intake_db=root / "intake.db",
            repository_db=root / "repository.db",
            vault_root=root / "vault",
            host="127.0.0.1",
            port=8790,
        )

    def _write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(CANDIDATE_TEMPLATE_FIELDS))
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def test_import_creates_queue_records_without_auto_approval_or_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            bootstrap_workspace(config)
            topic = WORKSPACE_TOPICS[0]
            csv_path = root / "candidates.csv"
            self._write_csv(
                csv_path,
                [
                    {
                        "title": "USFS Tree Field Guide",
                        "publisher": "United States Forest Service",
                        "url": "https://example.gov/usfs/trees",
                        "local_file_path": "",
                        "source_type": "government",
                        "mission_id": topic.mission_id,
                        "coverage_object_id": topic.coverage_object_id,
                        "proposed_canonical_reference_type": "government_publication",
                        "submitted_by": "human:researcher:001",
                        "license_status": "unknown_pending_review",
                        "license_notes": "License to be verified manually.",
                        "authority_score": "0.9",
                        "authority_reason": "Government forestry publisher.",
                        "risk_notes": "URL only; local file not yet acquired.",
                        "notes": "Real candidate submitted manually.",
                    }
                ],
            )

            result = import_candidates(csv_path, config)
            self.assertEqual(result["candidates_created"], 1)
            self.assertEqual(result["human_approvals_created"], 0)
            self.assertFalse(result["vault_sources_present"])

            records = OperationalRecords(config.intake_db)
            queue = CandidateIntakeQueue(config.intake_db, records=records)
            candidates = queue.list_candidates()
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["status"], "submitted")
            self.assertEqual(records.list_human_approvals(), [])

            summary = FoundryDataReader(config).dashboard_summary()
            self.assertEqual(summary["candidate_queue"]["total"], 1)

    def test_duplicate_candidate_import_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            bootstrap_workspace(config)
            topic = WORKSPACE_TOPICS[0]
            csv_path = root / "candidates.csv"
            row = {
                "title": "USFS Tree Field Guide",
                "publisher": "United States Forest Service",
                "url": "https://example.gov/usfs/trees",
                "local_file_path": "",
                "source_type": "government",
                "mission_id": topic.mission_id,
                "coverage_object_id": topic.coverage_object_id,
                "proposed_canonical_reference_type": "government_publication",
                "submitted_by": "human:researcher:001",
                "license_status": "",
                "license_notes": "",
                "authority_score": "",
                "authority_reason": "",
                "risk_notes": "",
                "notes": "",
            }
            self._write_csv(csv_path, [row, row])

            result = import_candidates(csv_path, config)
            self.assertEqual(result["candidates_created"], 2)
            self.assertEqual(result["duplicate_candidates"], 1)


if __name__ == "__main__":
    unittest.main()
