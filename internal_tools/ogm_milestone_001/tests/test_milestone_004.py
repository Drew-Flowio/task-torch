import tempfile
import unittest
from pathlib import Path

from internal_tools.ogm_milestone_001 import (
    CoverageStore,
    Curator001,
    IntakeLedger,
    OperationalRecords,
    RawSourceVault,
)


class Curator001Tests(unittest.TestCase):
    MISSION_ID = "mission:curator-001:north-american-outdoor:trees"
    COVERAGE_ID = "cov:ogm.pack.outdoor:species:trees:acer-rubrum"

    def _setup(self, root: Path):
        records = OperationalRecords(root / "intake.db")
        coverage = CoverageStore(root / "repository.db")
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
        return records, coverage, curator

    def _candidate(self) -> dict:
        return {
            "recommendation_id": "rec:curator-001:usfs-red-maple",
            "title": "Red Maple Species Profile",
            "publisher": "United States Forest Service",
            "url": "https://example.gov/usfs/red-maple",
            "source_type": "government",
            "authority_score": 0.95,
            "license_status": "public_domain_or_government_work",
            "coverage_contribution": "Satisfies government publication CRS for Red Maple.",
            "suggested_canonical_reference_type": "government_publication",
            "suggested_coverage_object_id": self.COVERAGE_ID,
            "reason_recommended": "Publisher is a government forestry authority.",
            "risks_limitations": ["Example URL used in local test fixture."],
        }

    def test_curator_can_load_mission(self):
        with tempfile.TemporaryDirectory() as tmp:
            _records, _coverage, curator = self._setup(Path(tmp))
            mission = curator.load_mission(self.MISSION_ID)
            self.assertEqual(mission["mission_id"], self.MISSION_ID)
            self.assertEqual(mission["target_pack_id"], Curator001.TARGET_PACK_ID)

            coverage_objects = curator.load_linked_coverage_objects(self.MISSION_ID)
            self.assertEqual(coverage_objects[0]["coverage_object_id"], self.COVERAGE_ID)

    def test_curator_identifies_missing_crs_requirements(self):
        with tempfile.TemporaryDirectory() as tmp:
            _records, _coverage, curator = self._setup(Path(tmp))
            missing = curator.identify_missing_crs_requirements(self.MISSION_ID)
            self.assertEqual(len(missing), 1)
            self.assertEqual(missing[0]["requirement"]["reference_type"], "government_publication")
            self.assertEqual(missing[0]["coverage_object"]["coverage_object_id"], self.COVERAGE_ID)

    def test_curator_creates_recommendation_records_for_manual_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            records, _coverage, curator = self._setup(Path(tmp))
            recommendations = curator.recommend_sources(
                self.MISSION_ID,
                candidates=[self._candidate()],
            )

            self.assertEqual(len(recommendations), 1)
            recommendation = recommendations[0]
            self.assertEqual(recommendation["recommendation_id"], "rec:curator-001:usfs-red-maple")
            self.assertEqual(recommendation["status"], "submitted")
            self.assertEqual(recommendation["metadata"]["title"], "Red Maple Species Profile")
            self.assertEqual(recommendation["metadata"]["publisher"], "United States Forest Service")
            self.assertEqual(recommendation["metadata"]["source_location"], "https://example.gov/usfs/red-maple")
            self.assertEqual(recommendation["metadata"]["authority_score"], 0.95)
            self.assertEqual(
                recommendation["metadata"]["suggested_canonical_reference_type"],
                "government_publication",
            )

            stored = records.get_curator_recommendation("rec:curator-001:usfs-red-maple")
            self.assertEqual(stored["metadata"]["manual_candidate"], True)

    def test_recommendation_records_link_to_coverage_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            records, _coverage, curator = self._setup(Path(tmp))
            curator.recommend_sources(self.MISSION_ID, candidates=[self._candidate()])

            linked = records.list_curator_recommendations(coverage_object_id=self.COVERAGE_ID)
            self.assertEqual(len(linked), 1)
            self.assertEqual(linked[0]["metadata"]["suggested_coverage_object_id"], self.COVERAGE_ID)

    def test_recommendations_require_human_approval_before_intake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records, _coverage, curator = self._setup(root)
            curator.recommend_sources(self.MISSION_ID, candidates=[self._candidate()])

            with self.assertRaises(PermissionError):
                curator.require_human_approval_for_intake("rec:curator-001:usfs-red-maple")

            approval = records.create_human_approval(
                approval_id="approval:curator-001:usfs-red-maple",
                mission_id=self.MISSION_ID,
                recommendation_id="rec:curator-001:usfs-red-maple",
                approver_id="human:reviewer:001",
                decision="approved",
                target_type="source_intake",
            )
            approved = curator.require_human_approval_for_intake("rec:curator-001:usfs-red-maple")
            self.assertEqual(approved["approval"]["approval_id"], approval["approval_id"])

            source_file = root / "red-maple.txt"
            source_file.write_text("Approved source content.\n", encoding="utf-8")
            ledger = IntakeLedger(root / "intake.db")
            vault = RawSourceVault(root / "vault", ledger)
            source = vault.store_approved_source(
                source_file,
                source="United States Forest Service",
                license="public_domain_or_government_work",
                mission=self.MISSION_ID,
                mission_id=self.MISSION_ID,
                curator=Curator001.CURATOR_ID,
                approval_status="approved",
                coverage_object_ids=[self.COVERAGE_ID],
                curator_recommendation_id="rec:curator-001:usfs-red-maple",
                human_approval_id=approval["approval_id"],
                source_quality_score=0.95,
                canonical_reference_type="government_publication",
            )
            self.assertEqual(source["curator_recommendation_id"], "rec:curator-001:usfs-red-maple")
            self.assertEqual(source["human_approval_id"], approval["approval_id"])

    def test_curator_avoids_low_quality_manual_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            _records, _coverage, curator = self._setup(Path(tmp))
            low_quality = {
                **self._candidate(),
                "recommendation_id": "rec:curator-001:seo-red-maple",
                "publisher": "Example SEO Farm",
                "source_type": "seo_content",
            }
            recommendations = curator.recommend_sources(self.MISSION_ID, candidates=[low_quality])
            self.assertEqual(recommendations, [])


if __name__ == "__main__":
    unittest.main()
