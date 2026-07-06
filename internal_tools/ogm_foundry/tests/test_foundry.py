import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from internal_tools.ogm_foundry.config import FoundryConfig
from internal_tools.ogm_foundry.data import FoundryDataReader
from internal_tools.ogm_foundry.server import create_server
from internal_tools.ogm_milestone_001 import (
    CandidateIntakeQueue,
    CoverageStore,
    Curator001,
    OperationalRecords,
)


class FoundryDataReaderTests(unittest.TestCase):
    def test_summary_returns_empty_states_without_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = FoundryConfig(
                data_root=root,
                intake_db=root / "intake.db",
                repository_db=root / "repository.db",
                vault_root=root / "vault",
                host="127.0.0.1",
                port=8790,
            )
            summary = FoundryDataReader(config).dashboard_summary()
            self.assertEqual(summary["repository"]["knowledge_objects"], 0)
            self.assertTrue(summary["repository"]["placeholder"])
            self.assertTrue(summary["candidate_queue"]["placeholder"])
            self.assertEqual(summary["health"]["status"], "degraded")

    def test_summary_reads_real_backend_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission_id = "mission:foundry:test"
            coverage_id = "cov:foundry:test"
            records = OperationalRecords(root / "intake.db")
            coverage = CoverageStore(root / "repository.db")
            queue = CandidateIntakeQueue(root / "intake.db", records=records)

            records.create_mission(
                mission_id=mission_id,
                title="Foundry test mission",
                target_pack_id=Curator001.TARGET_PACK_ID,
                metadata={"coverage_object_ids": [coverage_id]},
            )
            coverage.create_coverage_object(
                coverage_object_id=coverage_id,
                domain="outdoor",
                category="species",
                subcategory="trees",
                title="Test Tree",
            )
            queue.submit_candidate(
                candidate_id="cand:foundry:test",
                title="Test Candidate",
                publisher="USFS",
                url="https://example.gov/tree",
                source_type="government",
                submitted_by="human:tester",
                mission_id=mission_id,
                coverage_object_id=coverage_id,
                proposed_canonical_reference_type="government_publication",
            )

            config = FoundryConfig(
                data_root=root,
                intake_db=root / "intake.db",
                repository_db=root / "repository.db",
                vault_root=root / "vault",
                host="127.0.0.1",
                port=8790,
            )
            summary = FoundryDataReader(config).dashboard_summary()
            self.assertEqual(summary["missions"]["total"], 1)
            self.assertEqual(summary["coverage"]["total"], 1)
            self.assertEqual(summary["candidate_queue"]["total"], 1)
            self.assertFalse(summary["candidate_queue"]["placeholder"])


class FoundryServerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.config = FoundryConfig(
            data_root=self.root,
            intake_db=self.root / "intake.db",
            repository_db=self.root / "repository.db",
            vault_root=self.root / "vault",
            host="127.0.0.1",
            port=0,
        )
        self.server = create_server(self.config)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self._tmp.cleanup()

    def _get(self, path: str):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as response:
            return response.status, response.read()

    def test_dashboard_html_responds(self):
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"OFFGRID MINDS FOUNDRY", body)

    def test_dashboard_summary_api_responds(self):
        status, body = self._get("/api/dashboard/summary")
        self.assertEqual(status, 200)
        payload = json.loads(body.decode("utf-8"))
        self.assertIn("repository", payload)
        self.assertIn("health", payload)
        self.assertIn("recent_events", payload)

    def test_health_api_responds(self):
        status, body = self._get("/api/health")
        self.assertEqual(status, 200)
        payload = json.loads(body.decode("utf-8"))
        self.assertIn("status", payload)
        self.assertFalse(payload["capabilities"]["autonomous_crawling"])

    def test_unknown_api_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/unknown")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
