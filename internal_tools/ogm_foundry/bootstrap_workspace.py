"""Bootstrap the real North American Outdoor Expert Pack Foundry workspace."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from internal_tools.ogm_foundry.config import FoundryConfig
from internal_tools.ogm_foundry.workspace_spec import (
    PACK_ID,
    PACK_TITLE,
    WORKSPACE_ID,
    WORKSPACE_TOPICS,
    WORKSPACE_VERSION,
)
from internal_tools.ogm_milestone_001.coverage import CoverageStore
from internal_tools.ogm_milestone_001.records import OperationalRecords


MANIFEST_NAME = "workspace.json"


def manifest_path(config: FoundryConfig) -> Path:
    return config.data_root / MANIFEST_NAME


def workspace_exists(config: FoundryConfig) -> bool:
    if manifest_path(config).is_file():
        return True
    if config.intake_db.is_file():
        try:
            records = OperationalRecords(config.intake_db)
            for mission in records.list_missions():
                if mission.get("target_pack_id") == PACK_ID:
                    return True
        except Exception:
            return True
    return False


def reset_workspace(config: FoundryConfig) -> None:
    print("WARNING: Reset will permanently delete Foundry workspace data at:")
    print(f"  {config.data_root}")
    for target in (
        config.intake_db,
        config.repository_db,
        config.intake_db.with_suffix(".audit.jsonl"),
        config.repository_db.with_suffix(".audit.jsonl"),
        manifest_path(config),
    ):
        if target.is_file():
            target.unlink()
    if config.vault_root.is_dir():
        shutil.rmtree(config.vault_root)
    config.data_root.mkdir(parents=True, exist_ok=True)
    config.vault_root.mkdir(parents=True, exist_ok=True)


def bootstrap_workspace(
    config: FoundryConfig,
    *,
    force: bool = False,
    reset: bool = False,
) -> dict[str, Any]:
    if reset:
        reset_workspace(config)
    elif workspace_exists(config) and not force:
        raise RuntimeError(
            "Foundry workspace already exists. Re-run with --force to add missing records "
            "or --reset to delete and recreate the workspace."
        )

    config.data_root.mkdir(parents=True, exist_ok=True)
    config.vault_root.mkdir(parents=True, exist_ok=True)

    records = OperationalRecords(config.intake_db)
    coverage = CoverageStore(config.repository_db)

    created_missions: list[str] = []
    created_coverage: list[str] = []
    created_requirements: list[str] = []
    skipped_missions: list[str] = []
    skipped_coverage: list[str] = []

    for topic in WORKSPACE_TOPICS:
        try:
            coverage.get_coverage_object(topic.coverage_object_id)
            skipped_coverage.append(topic.coverage_object_id)
        except KeyError:
            coverage.create_coverage_object(
                coverage_object_id=topic.coverage_object_id,
                domain=topic.domain,
                category=topic.category,
                subcategory=topic.subcategory,
                title=topic.title,
                metadata={
                    "pack_id": PACK_ID,
                    "workspace_id": WORKSPACE_ID,
                    "topic_slug": topic.slug,
                },
            )
            created_coverage.append(topic.coverage_object_id)

        existing_requirements = {
            req["reference_type"]
            for req in coverage.list_canonical_reference_requirements(topic.coverage_object_id)
        }
        for requirement in topic.crs_requirements:
            if requirement.reference_type in existing_requirements:
                continue
            created = coverage.add_canonical_reference_requirement(
                coverage_object_id=topic.coverage_object_id,
                reference_type=requirement.reference_type,
                minimum_authority=requirement.minimum_authority,
                metadata={"label": requirement.label, "workspace_id": WORKSPACE_ID},
            )
            created_requirements.append(created["requirement_id"])

        try:
            records.get_mission(topic.mission_id)
            skipped_missions.append(topic.mission_id)
        except KeyError:
            records.create_mission(
                mission_id=topic.mission_id,
                title=topic.mission_title,
                status="active",
                target_pack_id=PACK_ID,
                metadata={
                    "workspace_id": WORKSPACE_ID,
                    "pack_title": PACK_TITLE,
                    "coverage_object_ids": [topic.coverage_object_id],
                    "topic_slug": topic.slug,
                    "topic_title": topic.title,
                },
            )
            created_missions.append(topic.mission_id)

    manifest = {
        "workspace_id": WORKSPACE_ID,
        "workspace_version": WORKSPACE_VERSION,
        "pack_id": PACK_ID,
        "pack_title": PACK_TITLE,
        "coverage_object_ids": [topic.coverage_object_id for topic in WORKSPACE_TOPICS],
        "mission_ids": [topic.mission_id for topic in WORKSPACE_TOPICS],
        "topics": [
            {
                "slug": topic.slug,
                "title": topic.title,
                "coverage_object_id": topic.coverage_object_id,
                "mission_id": topic.mission_id,
                "crs_requirement_count": len(topic.crs_requirements),
            }
            for topic in WORKSPACE_TOPICS
        ],
    }
    manifest_path(config).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return {
        "workspace_id": WORKSPACE_ID,
        "pack_id": PACK_ID,
        "data_root": str(config.data_root),
        "created_missions": created_missions,
        "created_coverage_objects": created_coverage,
        "created_crs_requirements": created_requirements,
        "skipped_missions": skipped_missions,
        "skipped_coverage_objects": skipped_coverage,
        "manifest": str(manifest_path(config)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the real Offgrid Minds Foundry workspace.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Create missing workspace records without deleting existing data.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing Foundry workspace data and recreate it.",
    )
    args = parser.parse_args(argv)
    config = FoundryConfig.from_env()

    try:
        result = bootstrap_workspace(config, force=args.force, reset=args.reset)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("Offgrid Minds Foundry workspace bootstrap complete.")
    print(f"Pack: {PACK_TITLE}")
    print(f"Data root: {result['data_root']}")
    print(f"Missions created: {len(result['created_missions'])}")
    print(f"Coverage objects created: {len(result['created_coverage_objects'])}")
    print(f"CRS requirements created: {len(result['created_crs_requirements'])}")
    if result["skipped_missions"]:
        print(f"Missions skipped (already exist): {len(result['skipped_missions'])}")
    print(f"Manifest: {result['manifest']}")
    print("No sources, approvals, vault records, or knowledge objects were created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
