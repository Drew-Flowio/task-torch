"""Coverage Matrix and CRS placeholder storage for Milestone 2."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from internal_tools.ogm_milestone_001.schema import migrate_repository_schema
from internal_tools.ogm_milestone_001.utils import json_dumps, json_loads, prefixed_uuid, utc_now_iso


class CoverageStore:
    """Minimal Coverage Object and CRS requirement registry."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            migrate_repository_schema(conn)

    def create_coverage_object(
        self,
        *,
        coverage_object_id: str,
        domain: str,
        category: str,
        title: str,
        subcategory: str | None = None,
        status: str = "not_started",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO coverage_objects (
                    coverage_object_id, domain, category, subcategory, title,
                    status, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    coverage_object_id,
                    domain,
                    category,
                    subcategory,
                    title,
                    status,
                    json_dumps(metadata or {}),
                    now,
                    now,
                ),
            )
        return self.get_coverage_object(coverage_object_id)

    def add_canonical_reference_requirement(
        self,
        *,
        coverage_object_id: str,
        reference_type: str,
        required: bool = True,
        minimum_authority: str | None = None,
        metadata: dict[str, Any] | None = None,
        requirement_id: str | None = None,
    ) -> dict[str, Any]:
        requirement_id = requirement_id or prefixed_uuid("crs")
        now = utc_now_iso()
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM coverage_objects WHERE coverage_object_id = ?",
                (coverage_object_id,),
            ).fetchone()
            if exists is None:
                raise KeyError(f"unknown coverage object: {coverage_object_id}")
            conn.execute(
                """
                INSERT INTO canonical_reference_requirements (
                    requirement_id, coverage_object_id, reference_type, required,
                    minimum_authority, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    requirement_id,
                    coverage_object_id,
                    reference_type,
                    1 if required else 0,
                    minimum_authority,
                    json_dumps(metadata or {}),
                    now,
                ),
            )
        return self.get_canonical_reference_requirement(requirement_id)

    def link_source_to_coverage(self, source_uuid: str, coverage_object_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO source_coverage_links (source_uuid, coverage_object_id)
                VALUES (?, ?)
                """,
                (source_uuid, coverage_object_id),
            )

    def link_evidence_to_coverage(self, evidence_uuid: str, coverage_object_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO evidence_coverage_links (evidence_uuid, coverage_object_id)
                VALUES (?, ?)
                """,
                (evidence_uuid, coverage_object_id),
            )

    def list_canonical_reference_requirements(self, coverage_object_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM canonical_reference_requirements
                WHERE coverage_object_id = ?
                ORDER BY created_at
                """,
                (coverage_object_id,),
            ).fetchall()
        return [self._requirement_from_row(row) for row in rows]

    def list_coverage_for_source_by_object(self, coverage_object_id: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT source_uuid FROM source_coverage_links WHERE coverage_object_id = ?",
                (coverage_object_id,),
            ).fetchall()
        return [row["source_uuid"] for row in rows]

    def list_coverage_for_evidence_by_object(self, coverage_object_id: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT evidence_uuid FROM evidence_coverage_links WHERE coverage_object_id = ?",
                (coverage_object_id,),
            ).fetchall()
        return [row["evidence_uuid"] for row in rows]

    def record_crs_satisfaction(
        self,
        *,
        requirement_id: str,
        coverage_object_id: str,
        reference_type: str,
        source_uuid: str | None = None,
        evidence_uuid: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        satisfaction_id = prefixed_uuid("crs-sat")
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO crs_satisfactions (
                    satisfaction_id, requirement_id, coverage_object_id, reference_type,
                    source_uuid, evidence_uuid, satisfied_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    satisfaction_id,
                    requirement_id,
                    coverage_object_id,
                    reference_type,
                    source_uuid,
                    evidence_uuid,
                    now,
                    json_dumps(metadata or {}),
                ),
            )
        return {
            "satisfaction_id": satisfaction_id,
            "requirement_id": requirement_id,
            "coverage_object_id": coverage_object_id,
            "reference_type": reference_type,
            "source_uuid": source_uuid,
            "evidence_uuid": evidence_uuid,
            "satisfied_at": now,
            "metadata": metadata or {},
        }

    def update_coverage_status(
        self,
        coverage_object_id: str,
        status: str,
        coverage_percentage: float,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE coverage_objects
                SET status = ?, coverage_percentage = ?, updated_at = ?
                WHERE coverage_object_id = ?
                """,
                (status, coverage_percentage, now, coverage_object_id),
            )
        return self.get_coverage_object(coverage_object_id)

    def create_mission_suggestion(
        self,
        *,
        mission_id: str,
        coverage_object_id: str,
        missing_reference_types: list[str],
        objective: str,
        priority: str = "high",
        status: str = "suggested",
        metadata: dict[str, Any] | None = None,
        suggestion_id: str | None = None,
    ) -> dict[str, Any]:
        suggestion_id = suggestion_id or prefixed_uuid("mis-sug")
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO mission_suggestions (
                    suggestion_id, mission_id, coverage_object_id,
                    missing_reference_types_json, objective, priority, status,
                    metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    suggestion_id,
                    mission_id,
                    coverage_object_id,
                    json_dumps(missing_reference_types),
                    objective,
                    priority,
                    status,
                    json_dumps(metadata or {}),
                    now,
                ),
            )
        return self.get_mission_suggestion(suggestion_id)

    def get_mission_suggestion(self, suggestion_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM mission_suggestions WHERE suggestion_id = ?",
                (suggestion_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown mission suggestion: {suggestion_id}")
        return {
            "suggestion_id": row["suggestion_id"],
            "mission_id": row["mission_id"],
            "coverage_object_id": row["coverage_object_id"],
            "missing_reference_types": json_loads(row["missing_reference_types_json"], []),
            "objective": row["objective"],
            "priority": row["priority"],
            "status": row["status"],
            "metadata": json_loads(row["metadata_json"], {}),
            "created_at": row["created_at"],
        }

    def list_coverage_objects(
        self,
        *,
        domain: str | None = None,
        category: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if domain is not None:
            clauses.append("domain = ?")
            params.append(domain)
        if category is not None:
            clauses.append("category = ?")
            params.append(category)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT coverage_object_id FROM coverage_objects {where} ORDER BY updated_at DESC",
                params,
            ).fetchall()
        return [self.get_coverage_object(row["coverage_object_id"]) for row in rows]

    def list_mission_suggestions(
        self,
        *,
        coverage_object_id: str | None = None,
        mission_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if coverage_object_id is not None:
            clauses.append("coverage_object_id = ?")
            params.append(coverage_object_id)
        if mission_id is not None:
            clauses.append("mission_id = ?")
            params.append(mission_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT suggestion_id FROM mission_suggestions {where} ORDER BY created_at",
                params,
            ).fetchall()
        return [self.get_mission_suggestion(row["suggestion_id"]) for row in rows]

    def get_coverage_object(self, coverage_object_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM coverage_objects WHERE coverage_object_id = ?",
                (coverage_object_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown coverage object: {coverage_object_id}")
        return {
            "coverage_object_id": row["coverage_object_id"],
            "domain": row["domain"],
            "category": row["category"],
            "subcategory": row["subcategory"],
            "title": row["title"],
            "status": row["status"],
            "coverage_percentage": row["coverage_percentage"] if "coverage_percentage" in row.keys() else 0.0,
            "metadata": json_loads(row["metadata_json"], {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_canonical_reference_requirement(self, requirement_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM canonical_reference_requirements WHERE requirement_id = ?",
                (requirement_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown CRS requirement: {requirement_id}")
        return self._requirement_from_row(row)

    def _requirement_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "requirement_id": row["requirement_id"],
            "coverage_object_id": row["coverage_object_id"],
            "reference_type": row["reference_type"],
            "required": bool(row["required"]),
            "minimum_authority": row["minimum_authority"],
            "metadata": json_loads(row["metadata_json"], {}),
            "created_at": row["created_at"],
        }

    def list_coverage_for_source(self, source_uuid: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT coverage_object_id FROM source_coverage_links WHERE source_uuid = ?",
                (source_uuid,),
            ).fetchall()
        return [row["coverage_object_id"] for row in rows]

    def list_coverage_for_evidence(self, evidence_uuid: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT coverage_object_id FROM evidence_coverage_links WHERE evidence_uuid = ?",
                (evidence_uuid,),
            ).fetchall()
        return [row["coverage_object_id"] for row in rows]
