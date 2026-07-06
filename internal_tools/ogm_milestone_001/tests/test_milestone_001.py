import sqlite3
import tempfile
import unittest
from pathlib import Path

from internal_tools.ogm_milestone_001 import (
    IntakeLedger,
    KnowledgeRepository,
    RawSourceVault,
)


class RawSourceVaultTests(unittest.TestCase):
    def test_store_approved_source_creates_immutable_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "sample.txt"
            sample.write_text("trusted source\n", encoding="utf-8")

            ledger = IntakeLedger(root / "intake.db")
            vault = RawSourceVault(root / "vault", ledger)
            record = vault.store_approved_source(
                sample,
                source="human upload",
                license="internal_test",
                mission="mission:vertical-slice-001",
                curator="curator-001",
                approval_status="approved",
                metadata={"coverage_object_id": "cov:test"},
                actor="human:reviewer:001",
            )

            self.assertTrue(record["uuid"].startswith("src:"))
            self.assertEqual(record["processing_state"], "raw_archived")
            self.assertEqual(record["mime_type"], "text/plain")
            self.assertTrue(record["revision"]["revision_uuid"].startswith("rev:"))
            self.assertTrue(vault.verify_revision(record["revision"]["revision_uuid"]))
            self.assertEqual(len(ledger.list_sources(mission="mission:vertical-slice-001")), 1)
            self.assertGreaterEqual(len(ledger.list_audit_events()), 3)

    def test_duplicate_checksum_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample_a = root / "a.txt"
            sample_b = root / "b.txt"
            sample_a.write_text("same\n", encoding="utf-8")
            sample_b.write_text("same\n", encoding="utf-8")

            ledger = IntakeLedger(root / "intake.db")
            vault = RawSourceVault(root / "vault", ledger)
            vault.store_approved_source(
                sample_a,
                source="human upload",
                license="internal_test",
                mission="mission:vertical-slice-001",
                curator="curator-001",
                approval_status="approved",
            )

            with self.assertRaises(ValueError):
                vault.store_approved_source(
                    sample_b,
                    source="human upload",
                    license="internal_test",
                    mission="mission:vertical-slice-001",
                    curator="curator-001",
                    approval_status="approved",
                )

    def test_unapproved_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "sample.txt"
            sample.write_text("not approved\n", encoding="utf-8")
            ledger = IntakeLedger(root / "intake.db")
            vault = RawSourceVault(root / "vault", ledger)

            with self.assertRaises(ValueError):
                vault.store_approved_source(
                    sample,
                    source="human upload",
                    license="internal_test",
                    mission="mission:vertical-slice-001",
                    curator="curator-001",
                    approval_status="pending",
                )


class KnowledgeRepositoryTests(unittest.TestCase):
    def _source_and_repo(self, root: Path):
        sample = root / "source.txt"
        sample.write_text("Step 1: Bring water to a rolling boil.\n", encoding="utf-8")
        ledger = IntakeLedger(root / "intake.db")
        vault = RawSourceVault(root / "vault", ledger)
        source = vault.store_approved_source(
            sample,
            source="human upload",
            license="internal_test",
            mission="mission:vertical-slice-001",
            curator="curator-001",
            approval_status="approved",
        )
        repo = KnowledgeRepository(root / "repository.db")
        return source, repo

    def test_create_evidence_and_knowledge_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, repo = self._source_and_repo(root)

            evidence = repo.create_evidence(
                source_uuid=source["uuid"],
                raw_revision_uuid=source["revision"]["revision_uuid"],
                locator={"type": "line", "line": 1},
                citation={"title": source["filename"], "locator": "line 1"},
            )
            obj = repo.create_knowledge_object(
                canonical_key="outdoor:procedure:boil-water",
                category="Procedure",
                title="Boil water",
                summary="Bring water to a rolling boil.",
                body={"format": "plain", "value": "Bring water to a rolling boil."},
                provenance={
                    "mission": "mission:vertical-slice-001",
                    "curator": "curator-001",
                    "source_uuid": source["uuid"],
                },
                confidence={"overall": 0.95},
                metadata={"domains": ["outdoor"]},
                evidence_refs=[evidence["evidence_uuid"]],
            )

            self.assertTrue(obj["object_uuid"].startswith("rko:"))
            self.assertEqual(obj["category"], "Procedure")
            self.assertEqual(obj["evidence_refs"], [evidence["evidence_uuid"]])
            self.assertIsNotNone(obj["current_revision_uuid"])
            self.assertGreaterEqual(len(repo.list_audit_events()), 3)

    def test_relationships_have_ids_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, repo = self._source_and_repo(root)
            evidence = repo.create_evidence(
                source_uuid=source["uuid"],
                raw_revision_uuid=source["revision"]["revision_uuid"],
                locator={"type": "line", "line": 1},
                citation={"title": source["filename"]},
            )
            warning = repo.create_knowledge_object(
                canonical_key="outdoor:warning:burn-risk",
                category="SafetyWarning",
                title="Burn risk",
                summary="Boiling water can burn skin.",
                body={"format": "plain", "value": "Avoid contact with boiling water."},
                provenance={"source_uuid": source["uuid"]},
                confidence={"overall": 0.9},
                evidence_refs=[evidence["evidence_uuid"]],
            )
            procedure = repo.create_knowledge_object(
                canonical_key="outdoor:procedure:boil-water",
                category="Procedure",
                title="Boil water",
                summary="Bring water to a rolling boil.",
                body={"format": "plain", "value": "Bring water to a rolling boil."},
                provenance={"source_uuid": source["uuid"]},
                confidence={"overall": 0.95},
                evidence_refs=[evidence["evidence_uuid"]],
            )

            rel = repo.create_relationship(
                from_object_uuid=procedure["object_uuid"],
                to_object_uuid=warning["object_uuid"],
                relationship_type="has_warning",
                evidence_refs=[evidence["evidence_uuid"]],
                confidence=0.93,
            )

            self.assertTrue(rel["relationship_uuid"].startswith("rel:"))
            self.assertEqual(rel["evidence_refs"], [evidence["evidence_uuid"]])
            self.assertEqual(len(repo.list_relationships(object_uuid=procedure["object_uuid"])), 1)

    def test_duplicate_canonical_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, repo = self._source_and_repo(root)
            evidence = repo.create_evidence(
                source_uuid=source["uuid"],
                raw_revision_uuid=source["revision"]["revision_uuid"],
                locator={"type": "line", "line": 1},
                citation={"title": source["filename"]},
            )
            kwargs = {
                "canonical_key": "outdoor:procedure:boil-water",
                "category": "Procedure",
                "title": "Boil water",
                "summary": "Bring water to a rolling boil.",
                "body": {"format": "plain", "value": "Bring water to a rolling boil."},
                "provenance": {"source_uuid": source["uuid"]},
                "confidence": {"overall": 0.95},
                "evidence_refs": [evidence["evidence_uuid"]],
            }
            repo.create_knowledge_object(**kwargs)
            with self.assertRaises(sqlite3.IntegrityError):
                repo.create_knowledge_object(**kwargs)

    def test_missing_provenance_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = KnowledgeRepository(Path(tmp) / "repository.db")
            with self.assertRaises(ValueError):
                repo.create_knowledge_object(
                    canonical_key="bad",
                    category="Procedure",
                    title="Bad object",
                    summary="Missing provenance.",
                    body={"format": "plain", "value": "bad"},
                    provenance={},
                    confidence={"overall": 0.5},
                )


if __name__ == "__main__":
    unittest.main()
