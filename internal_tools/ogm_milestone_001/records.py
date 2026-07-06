"""First-class operational records for missions, recommendations, and approvals."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from internal_tools.ogm_milestone_001.schema import migrate_intake_operational_schema
from internal_tools.ogm_milestone_001.utils import json_dumps, json_loads, prefixed_uuid, utc_now_iso


class OperationalRecords:
    """Local registry for missions, curator recommendations, and human approvals."""

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
            migrate_intake_operational_schema(conn)

    def create_mission(
        self,
        *,
        mission_id: str,
        title: str,
        status: str = "active",
        target_pack_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO missions (
                    mission_id, title, status, target_pack_id, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mission_id,
                    title,
                    status,
                    target_pack_id,
                    json_dumps(metadata or {}),
                    now,
                    now,
                ),
            )
        return self.get_mission(mission_id)

    def create_curator_recommendation(
        self,
        *,
        recommendation_id: str,
        mission_id: str,
        curator_id: str,
        source_label: str,
        status: str = "submitted",
        metadata: dict[str, Any] | None = None,
        title: str | None = None,
        publisher: str | None = None,
        source_location: str | None = None,
        source_type: str | None = None,
        authority_score: float | None = None,
        license_status: str | None = None,
        coverage_contribution: str | None = None,
        suggested_canonical_reference_type: str | None = None,
        suggested_coverage_object_id: str | None = None,
        reason_recommended: str | None = None,
        risks_limitations: list[str] | None = None,
    ) -> dict[str, Any]:
        self.get_mission(mission_id)
        if authority_score is not None and not 0 <= authority_score <= 1:
            raise ValueError("authority_score must be between 0 and 1")
        recommendation_metadata = {
            **(metadata or {}),
            **{
                key: value
                for key, value in {
                    "title": title,
                    "publisher": publisher,
                    "source_location": source_location,
                    "source_type": source_type,
                    "authority_score": authority_score,
                    "license_status": license_status,
                    "coverage_contribution": coverage_contribution,
                    "suggested_canonical_reference_type": suggested_canonical_reference_type,
                    "suggested_coverage_object_id": suggested_coverage_object_id,
                    "reason_recommended": reason_recommended,
                    "risks_limitations": risks_limitations,
                }.items()
                if value is not None
            },
        }
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO curator_recommendations (
                    recommendation_id, mission_id, curator_id, source_label, status,
                    metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recommendation_id,
                    mission_id,
                    curator_id,
                    source_label,
                    status,
                    json_dumps(recommendation_metadata),
                    now,
                ),
            )
        return self.get_curator_recommendation(recommendation_id)

    def create_human_approval(
        self,
        *,
        approval_id: str,
        mission_id: str,
        approver_id: str,
        decision: str,
        target_type: str,
        recommendation_id: str | None = None,
        target_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.get_mission(mission_id)
        if recommendation_id is not None:
            self.get_curator_recommendation(recommendation_id)
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO human_approvals (
                    approval_id, mission_id, recommendation_id, approver_id, decision,
                    target_type, target_id, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    mission_id,
                    recommendation_id,
                    approver_id,
                    decision,
                    target_type,
                    target_id,
                    json_dumps(metadata or {}),
                    now,
                ),
            )
        return self.get_human_approval(approval_id)

    def get_mission(self, mission_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM missions WHERE mission_id = ?", (mission_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown mission: {mission_id}")
        return {
            "mission_id": row["mission_id"],
            "title": row["title"],
            "status": row["status"],
            "target_pack_id": row["target_pack_id"],
            "metadata": json_loads(row["metadata_json"], {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_curator_recommendation(self, recommendation_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM curator_recommendations WHERE recommendation_id = ?",
                (recommendation_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown curator recommendation: {recommendation_id}")
        return {
            "recommendation_id": row["recommendation_id"],
            "mission_id": row["mission_id"],
            "curator_id": row["curator_id"],
            "source_label": row["source_label"],
            "status": row["status"],
            "metadata": json_loads(row["metadata_json"], {}),
            "created_at": row["created_at"],
        }

    def get_human_approval(self, approval_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM human_approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown human approval: {approval_id}")
        return {
            "approval_id": row["approval_id"],
            "mission_id": row["mission_id"],
            "recommendation_id": row["recommendation_id"],
            "approver_id": row["approver_id"],
            "decision": row["decision"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "metadata": json_loads(row["metadata_json"], {}),
            "created_at": row["created_at"],
        }

    def list_curator_recommendations(
        self,
        *,
        mission_id: str | None = None,
        status: str | None = None,
        coverage_object_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if mission_id is not None:
            clauses.append("mission_id = ?")
            params.append(mission_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT recommendation_id FROM curator_recommendations {where} ORDER BY created_at",
                params,
            ).fetchall()
        recommendations = [self.get_curator_recommendation(row["recommendation_id"]) for row in rows]
        if coverage_object_id is not None:
            recommendations = [
                recommendation
                for recommendation in recommendations
                if recommendation["metadata"].get("suggested_coverage_object_id") == coverage_object_id
            ]
        return recommendations

    def get_approved_recommendation_for_intake(self, recommendation_id: str) -> dict[str, Any]:
        recommendation = self.get_curator_recommendation(recommendation_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT approval_id FROM human_approvals
                WHERE recommendation_id = ?
                  AND target_type = 'source_intake'
                  AND decision = 'approved'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (recommendation_id,),
            ).fetchone()
        if row is None:
            raise PermissionError("recommendation requires human approval before source intake")
        approval = self.get_human_approval(row["approval_id"])
        return {"recommendation": recommendation, "approval": approval}

    def list_human_approvals(
        self,
        *,
        mission_id: str | None = None,
        decision: str | None = None,
        target_type: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if mission_id is not None:
            clauses.append("mission_id = ?")
            params.append(mission_id)
        if decision is not None:
            clauses.append("decision = ?")
            params.append(decision)
        if target_type is not None:
            clauses.append("target_type = ?")
            params.append(target_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT approval_id FROM human_approvals {where} ORDER BY created_at DESC",
                params,
            ).fetchall()
        return [self.get_human_approval(row["approval_id"]) for row in rows]

    def list_missions(self, *, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM missions"
        params: tuple[Any, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY created_at"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "mission_id": row["mission_id"],
                "title": row["title"],
                "status": row["status"],
                "target_pack_id": row["target_pack_id"],
                "metadata": json_loads(row["metadata_json"], {}),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]
