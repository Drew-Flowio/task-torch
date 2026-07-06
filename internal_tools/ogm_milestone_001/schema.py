"""Schema migration helpers for Milestone 1/2 SQLite databases."""

from __future__ import annotations

import sqlite3


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def migrate_intake_schema(conn: sqlite3.Connection) -> None:
    """Add Milestone 2 structured intake columns to existing databases."""

    columns = _table_columns(conn, "sources")
    additions = {
        "mission_id": "TEXT",
        "coverage_object_ids_json": "TEXT NOT NULL DEFAULT '[]'",
        "curator_recommendation_id": "TEXT",
        "human_approval_id": "TEXT",
        "source_quality_score": "REAL",
        "canonical_reference_type": "TEXT",
    }
    for name, ddl in additions.items():
        if name not in columns:
            conn.execute(f"ALTER TABLE sources ADD COLUMN {name} {ddl}")

    conn.execute(
        """
        UPDATE sources
        SET mission_id = mission
        WHERE mission_id IS NULL OR mission_id = ''
        """
    )


def migrate_repository_schema(conn: sqlite3.Connection) -> None:
    """Add Milestone 2 coverage and CRS placeholder tables."""

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS coverage_objects (
            coverage_object_id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'not_started',
            coverage_percentage REAL NOT NULL DEFAULT 0.0,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS canonical_reference_requirements (
            requirement_id TEXT PRIMARY KEY,
            coverage_object_id TEXT NOT NULL,
            reference_type TEXT NOT NULL,
            required INTEGER NOT NULL DEFAULT 1,
            minimum_authority TEXT,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(coverage_object_id) REFERENCES coverage_objects(coverage_object_id)
        );

        CREATE TABLE IF NOT EXISTS source_coverage_links (
            source_uuid TEXT NOT NULL,
            coverage_object_id TEXT NOT NULL,
            PRIMARY KEY(source_uuid, coverage_object_id)
        );

        CREATE TABLE IF NOT EXISTS evidence_coverage_links (
            evidence_uuid TEXT NOT NULL,
            coverage_object_id TEXT NOT NULL,
            PRIMARY KEY(evidence_uuid, coverage_object_id)
        );

        CREATE TABLE IF NOT EXISTS crs_satisfactions (
            satisfaction_id TEXT PRIMARY KEY,
            requirement_id TEXT NOT NULL,
            coverage_object_id TEXT NOT NULL,
            reference_type TEXT NOT NULL,
            source_uuid TEXT,
            evidence_uuid TEXT,
            satisfied_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            FOREIGN KEY(requirement_id) REFERENCES canonical_reference_requirements(requirement_id),
            FOREIGN KEY(coverage_object_id) REFERENCES coverage_objects(coverage_object_id)
        );

        CREATE TABLE IF NOT EXISTS mission_suggestions (
            suggestion_id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL,
            coverage_object_id TEXT NOT NULL,
            missing_reference_types_json TEXT NOT NULL,
            objective TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(coverage_object_id) REFERENCES coverage_objects(coverage_object_id)
        );
        """
    )
    columns = _table_columns(conn, "coverage_objects")
    if "coverage_percentage" not in columns:
        conn.execute(
            "ALTER TABLE coverage_objects ADD COLUMN coverage_percentage REAL NOT NULL DEFAULT 0.0"
        )


def migrate_intake_operational_schema(conn: sqlite3.Connection) -> None:
    """Add operational records to the intake database."""

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS missions (
            mission_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            target_pack_id TEXT,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS curator_recommendations (
            recommendation_id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL,
            curator_id TEXT NOT NULL,
            source_label TEXT NOT NULL,
            status TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(mission_id) REFERENCES missions(mission_id)
        );

        CREATE TABLE IF NOT EXISTS human_approvals (
            approval_id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL,
            recommendation_id TEXT,
            approver_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(mission_id) REFERENCES missions(mission_id),
            FOREIGN KEY(recommendation_id) REFERENCES curator_recommendations(recommendation_id)
        );

        CREATE TABLE IF NOT EXISTS candidate_sources (
            candidate_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            publisher TEXT NOT NULL,
            source_location TEXT NOT NULL,
            normalized_url TEXT,
            local_file_path TEXT,
            file_checksum TEXT,
            source_type TEXT NOT NULL,
            submitted_by TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            mission_id TEXT NOT NULL,
            coverage_object_id TEXT NOT NULL,
            proposed_canonical_reference_type TEXT NOT NULL,
            notes TEXT,
            status TEXT NOT NULL,
            license_status TEXT,
            license_notes TEXT,
            license_source_url TEXT,
            license_text_excerpt TEXT,
            license_checked_at TEXT,
            license_checked_by TEXT,
            authority_score REAL,
            authority_reason TEXT,
            risk_notes TEXT,
            reviewer_notes TEXT,
            assigned_reviewer TEXT,
            review_due_at TEXT,
            review_priority TEXT,
            duplicate_of_candidate_id TEXT,
            curator_recommendation_id TEXT,
            metadata_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(mission_id) REFERENCES missions(mission_id),
            FOREIGN KEY(curator_recommendation_id) REFERENCES curator_recommendations(recommendation_id)
        );

        CREATE TABLE IF NOT EXISTS candidate_review_events (
            event_id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            actor TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT NOT NULL,
            reason TEXT,
            notes TEXT,
            metadata_json TEXT NOT NULL,
            FOREIGN KEY(candidate_id) REFERENCES candidate_sources(candidate_id)
        );
        """
    )

    columns = _table_columns(conn, "candidate_sources")
    additions = {
        "license_source_url": "TEXT",
        "license_text_excerpt": "TEXT",
        "license_checked_at": "TEXT",
        "license_checked_by": "TEXT",
        "assigned_reviewer": "TEXT",
        "review_due_at": "TEXT",
        "review_priority": "TEXT",
    }
    for name, ddl in additions.items():
        if name not in columns:
            conn.execute(f"ALTER TABLE candidate_sources ADD COLUMN {name} {ddl}")
