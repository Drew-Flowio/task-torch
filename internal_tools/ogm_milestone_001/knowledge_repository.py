"""Minimal Knowledge Repository Core for Milestone 1."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from internal_tools.ogm_milestone_001.audit import AuditLog
from internal_tools.ogm_milestone_001.acp_events import (
    emit_acp_events,
    prepare_repository_object_created_event,
)
from internal_tools.ogm_milestone_001.review import validate_transition
from internal_tools.ogm_milestone_001.schema import migrate_repository_schema
from internal_tools.ogm_milestone_001.utils import json_dumps, json_loads, prefixed_uuid, utc_now_iso


class KnowledgeRepository:
    """Stores repository Knowledge Objects, evidence, relationships, and revisions."""

    def __init__(
        self,
        db_path: str | Path,
        audit_log: AuditLog | None = None,
        acp_log_store: Any | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_log = audit_log or AuditLog(self.db_path.with_suffix(".audit.jsonl"))
        self.acp_log_store = acp_log_store
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
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_objects (
                    object_uuid TEXT PRIMARY KEY,
                    canonical_key TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    body_json TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    confidence_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_revision_uuid TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS object_revisions (
                    revision_uuid TEXT PRIMARY KEY,
                    object_uuid TEXT NOT NULL,
                    version TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(object_uuid) REFERENCES knowledge_objects(object_uuid)
                );

                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_uuid TEXT PRIMARY KEY,
                    source_uuid TEXT NOT NULL,
                    raw_revision_uuid TEXT NOT NULL,
                    locator_json TEXT NOT NULL,
                    citation_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS object_evidence (
                    object_uuid TEXT NOT NULL,
                    evidence_uuid TEXT NOT NULL,
                    role TEXT NOT NULL,
                    PRIMARY KEY(object_uuid, evidence_uuid, role),
                    FOREIGN KEY(object_uuid) REFERENCES knowledge_objects(object_uuid),
                    FOREIGN KEY(evidence_uuid) REFERENCES evidence(evidence_uuid)
                );

                CREATE TABLE IF NOT EXISTS relationships (
                    relationship_uuid TEXT PRIMARY KEY,
                    from_object_uuid TEXT NOT NULL,
                    to_object_uuid TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    evidence_refs_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(from_object_uuid) REFERENCES knowledge_objects(object_uuid),
                    FOREIGN KEY(to_object_uuid) REFERENCES knowledge_objects(object_uuid)
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    audit_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                """
            )
            migrate_repository_schema(conn)

    def create_evidence(
        self,
        *,
        source_uuid: str,
        raw_revision_uuid: str,
        locator: dict[str, Any],
        citation: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        evidence_uuid: str | None = None,
        actor: str = "system",
    ) -> dict[str, Any]:
        if not locator:
            raise ValueError("evidence locator is required")
        if not citation:
            raise ValueError("citation is required")

        evidence_uuid = evidence_uuid or prefixed_uuid("ev")
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO evidence (
                    evidence_uuid, source_uuid, raw_revision_uuid, locator_json,
                    citation_json, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_uuid,
                    source_uuid,
                    raw_revision_uuid,
                    json_dumps(locator),
                    json_dumps(citation),
                    json_dumps(metadata or {}),
                    now,
                ),
            )
        self.record_audit(
            action="evidence_created",
            entity_type="evidence",
            entity_id=evidence_uuid,
            actor=actor,
            details={"source_uuid": source_uuid, "raw_revision_uuid": raw_revision_uuid},
        )
        return self.get_evidence(evidence_uuid)

    def create_knowledge_object(
        self,
        *,
        canonical_key: str,
        category: str,
        title: str,
        summary: str,
        body: dict[str, Any],
        provenance: dict[str, Any],
        confidence: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        evidence_refs: list[str] | None = None,
        version: str = "1.0.0",
        status: str = "candidate",
        object_uuid: str | None = None,
        actor: str = "system",
    ) -> dict[str, Any]:
        self._validate_object_inputs(
            canonical_key=canonical_key,
            body=body,
            provenance=provenance,
            confidence=confidence,
        )

        object_uuid = object_uuid or prefixed_uuid("rko")
        now = utc_now_iso()
        metadata = metadata or {}
        evidence_refs = evidence_refs or []

        with self._connect() as conn:
            for evidence_uuid in evidence_refs:
                exists = conn.execute(
                    "SELECT 1 FROM evidence WHERE evidence_uuid = ?",
                    (evidence_uuid,),
                ).fetchone()
                if exists is None:
                    raise KeyError(f"unknown evidence: {evidence_uuid}")

            conn.execute(
                """
                INSERT INTO knowledge_objects (
                    object_uuid, canonical_key, category, title, summary, body_json,
                    provenance_json, confidence_json, metadata_json, version, status,
                    current_revision_uuid, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    object_uuid,
                    canonical_key,
                    category,
                    title,
                    summary,
                    json_dumps(body),
                    json_dumps(provenance),
                    json_dumps(confidence),
                    json_dumps(metadata),
                    version,
                    status,
                    now,
                    now,
                ),
            )
            for evidence_uuid in evidence_refs:
                conn.execute(
                    """
                    INSERT INTO object_evidence (object_uuid, evidence_uuid, role)
                    VALUES (?, ?, ?)
                    """,
                    (object_uuid, evidence_uuid, "supporting"),
                )

        revision = self.create_revision(
            object_uuid=object_uuid,
            change_type="initial_create",
            actor=actor,
        )
        self.record_audit(
            action="knowledge_object_created",
            entity_type="knowledge_object",
            entity_id=object_uuid,
            actor=actor,
            details={"category": category, "revision_uuid": revision["revision_uuid"]},
        )
        mission_id = provenance.get("mission_id") or provenance.get("mission") or "mission:system"
        if self.acp_log_store is not None:
            emit_acp_events(
                [
                    prepare_repository_object_created_event(
                        object_uuid=object_uuid,
                        category=category,
                        title=title,
                        mission_id=mission_id,
                        evidence_refs=evidence_refs,
                    )
                ],
                log_store=self.acp_log_store,
            )
        return self.get_knowledge_object(object_uuid)

    def create_relationship(
        self,
        *,
        from_object_uuid: str,
        to_object_uuid: str,
        relationship_type: str,
        evidence_refs: list[str] | None = None,
        confidence: float = 1.0,
        status: str = "candidate",
        metadata: dict[str, Any] | None = None,
        relationship_uuid: str | None = None,
        actor: str = "system",
    ) -> dict[str, Any]:
        if from_object_uuid == to_object_uuid:
            raise ValueError("relationship cannot point to the same object")
        if not 0 <= confidence <= 1:
            raise ValueError("relationship confidence must be between 0 and 1")

        relationship_uuid = relationship_uuid or prefixed_uuid("rel")
        evidence_refs = evidence_refs or []
        now = utc_now_iso()

        with self._connect() as conn:
            for object_uuid in (from_object_uuid, to_object_uuid):
                if conn.execute("SELECT 1 FROM knowledge_objects WHERE object_uuid = ?", (object_uuid,)).fetchone() is None:
                    raise KeyError(f"unknown knowledge object: {object_uuid}")
            for evidence_uuid in evidence_refs:
                if conn.execute("SELECT 1 FROM evidence WHERE evidence_uuid = ?", (evidence_uuid,)).fetchone() is None:
                    raise KeyError(f"unknown evidence: {evidence_uuid}")

            conn.execute(
                """
                INSERT INTO relationships (
                    relationship_uuid, from_object_uuid, to_object_uuid, relationship_type,
                    evidence_refs_json, confidence, status, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relationship_uuid,
                    from_object_uuid,
                    to_object_uuid,
                    relationship_type,
                    json_dumps(evidence_refs),
                    confidence,
                    status,
                    json_dumps(metadata or {}),
                    now,
                ),
            )

        self.record_audit(
            action="relationship_created",
            entity_type="relationship",
            entity_id=relationship_uuid,
            actor=actor,
            details={
                "from_object_uuid": from_object_uuid,
                "to_object_uuid": to_object_uuid,
                "relationship_type": relationship_type,
            },
        )
        return self.get_relationship(relationship_uuid)

    def transition_object_status(
        self,
        object_uuid: str,
        new_status: str,
        *,
        actor: str = "system",
        reason: str | None = None,
    ) -> dict[str, Any]:
        obj = self.get_knowledge_object(object_uuid, include_relationships=False)
        validate_transition(obj["status"], new_status, entity_label="object")
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                "UPDATE knowledge_objects SET status = ?, updated_at = ? WHERE object_uuid = ?",
                (new_status, now, object_uuid),
            )
        self.record_audit(
            action="knowledge_object_status_changed",
            entity_type="knowledge_object",
            entity_id=object_uuid,
            actor=actor,
            details={
                "from_status": obj["status"],
                "to_status": new_status,
                "reason": reason,
            },
        )
        return self.get_knowledge_object(object_uuid, include_relationships=False)

    def transition_relationship_status(
        self,
        relationship_uuid: str,
        new_status: str,
        *,
        actor: str = "system",
        reason: str | None = None,
    ) -> dict[str, Any]:
        rel = self.get_relationship(relationship_uuid)
        validate_transition(rel["status"], new_status, entity_label="relationship")
        with self._connect() as conn:
            conn.execute(
                "UPDATE relationships SET status = ? WHERE relationship_uuid = ?",
                (new_status, relationship_uuid),
            )
        self.record_audit(
            action="relationship_status_changed",
            entity_type="relationship",
            entity_id=relationship_uuid,
            actor=actor,
            details={
                "from_status": rel["status"],
                "to_status": new_status,
                "reason": reason,
            },
        )
        return self.get_relationship(relationship_uuid)

    def create_revision(
        self,
        *,
        object_uuid: str,
        change_type: str,
        actor: str = "system",
    ) -> dict[str, Any]:
        obj = self.get_knowledge_object(object_uuid, include_relationships=False)
        revision_uuid = prefixed_uuid("rev")
        now = utc_now_iso()
        snapshot = {
            "object": obj,
            "evidence_refs": self.list_object_evidence(object_uuid),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO object_revisions (
                    revision_uuid, object_uuid, version, change_type, snapshot_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    revision_uuid,
                    object_uuid,
                    obj["version"],
                    change_type,
                    json_dumps(snapshot),
                    now,
                ),
            )
            conn.execute(
                "UPDATE knowledge_objects SET current_revision_uuid = ?, updated_at = ? WHERE object_uuid = ?",
                (revision_uuid, now, object_uuid),
            )
        self.record_audit(
            action="object_revision_created",
            entity_type="object_revision",
            entity_id=revision_uuid,
            actor=actor,
            details={"object_uuid": object_uuid, "change_type": change_type},
        )
        return self.get_revision(revision_uuid)

    def get_knowledge_object(self, object_uuid: str, *, include_relationships: bool = True) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge_objects WHERE object_uuid = ?",
                (object_uuid,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown knowledge object: {object_uuid}")
        obj = self._object_from_row(row)
        obj["evidence_refs"] = self.list_object_evidence(object_uuid)
        if include_relationships:
            obj["relationships"] = self.list_relationships(object_uuid=object_uuid)
        return obj

    def get_evidence(self, evidence_uuid: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM evidence WHERE evidence_uuid = ?",
                (evidence_uuid,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown evidence: {evidence_uuid}")
        return self._evidence_from_row(row)

    def get_relationship(self, relationship_uuid: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM relationships WHERE relationship_uuid = ?",
                (relationship_uuid,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown relationship: {relationship_uuid}")
        return self._relationship_from_row(row)

    def get_revision(self, revision_uuid: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM object_revisions WHERE revision_uuid = ?",
                (revision_uuid,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown object revision: {revision_uuid}")
        return {
            "revision_uuid": row["revision_uuid"],
            "object_uuid": row["object_uuid"],
            "version": row["version"],
            "change_type": row["change_type"],
            "snapshot": json_loads(row["snapshot_json"], {}),
            "created_at": row["created_at"],
        }

    def list_object_evidence(self, object_uuid: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT evidence_uuid FROM object_evidence WHERE object_uuid = ? ORDER BY evidence_uuid",
                (object_uuid,),
            ).fetchall()
        return [row["evidence_uuid"] for row in rows]

    def list_relationships(self, *, object_uuid: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM relationships"
        params: tuple[Any, ...] = ()
        if object_uuid is not None:
            query += " WHERE from_object_uuid = ? OR to_object_uuid = ?"
            params = (object_uuid, object_uuid)
        query += " ORDER BY created_at"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._relationship_from_row(row) for row in rows]

    def list_evidence(self, *, source_uuid: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM evidence"
        params: tuple[Any, ...] = ()
        if source_uuid is not None:
            query += " WHERE source_uuid = ?"
            params = (source_uuid,)
        query += " ORDER BY created_at"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._evidence_from_row(row) for row in rows]

    def list_objects(self, *, category: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if category is not None:
            clauses.append("category = ?")
            params.append(category)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(f"SELECT * FROM knowledge_objects {where} ORDER BY created_at", params).fetchall()
        return [self._object_from_row(row) for row in rows]

    def record_audit(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        actor: str = "system",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = self.audit_log.append(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            details=details or {},
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (
                    audit_id, timestamp, actor, action, entity_type, entity_id, details_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["audit_id"],
                    event["timestamp"],
                    event["actor"],
                    event["action"],
                    event["entity_type"],
                    event["entity_id"],
                    json_dumps(event["details"]),
                ),
            )
        return event

    def list_audit_events(self, entity_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM audit_events"
        params: tuple[Any, ...] = ()
        if entity_id is not None:
            query += " WHERE entity_id = ?"
            params = (entity_id,)
        query += " ORDER BY timestamp"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "audit_id": row["audit_id"],
                "timestamp": row["timestamp"],
                "actor": row["actor"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "details": json_loads(row["details_json"], {}),
            }
            for row in rows
        ]

    def _validate_object_inputs(
        self,
        *,
        canonical_key: str,
        body: dict[str, Any],
        provenance: dict[str, Any],
        confidence: dict[str, Any],
    ) -> None:
        if not canonical_key:
            raise ValueError("canonical_key is required to prevent duplicate canonical knowledge")
        if not body:
            raise ValueError("body is required")
        if not provenance:
            raise ValueError("provenance is required")
        if "overall" not in confidence:
            raise ValueError("confidence.overall is required")
        if not 0 <= float(confidence["overall"]) <= 1:
            raise ValueError("confidence.overall must be between 0 and 1")

    def _object_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "object_uuid": row["object_uuid"],
            "canonical_key": row["canonical_key"],
            "category": row["category"],
            "title": row["title"],
            "summary": row["summary"],
            "body": json_loads(row["body_json"], {}),
            "provenance": json_loads(row["provenance_json"], {}),
            "confidence": json_loads(row["confidence_json"], {}),
            "metadata": json_loads(row["metadata_json"], {}),
            "version": row["version"],
            "status": row["status"],
            "current_revision_uuid": row["current_revision_uuid"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _evidence_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "evidence_uuid": row["evidence_uuid"],
            "source_uuid": row["source_uuid"],
            "raw_revision_uuid": row["raw_revision_uuid"],
            "locator": json_loads(row["locator_json"], {}),
            "citation": json_loads(row["citation_json"], {}),
            "metadata": json_loads(row["metadata_json"], {}),
            "created_at": row["created_at"],
        }

    def _relationship_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "relationship_uuid": row["relationship_uuid"],
            "from_object_uuid": row["from_object_uuid"],
            "to_object_uuid": row["to_object_uuid"],
            "relationship_type": row["relationship_type"],
            "evidence_refs": json_loads(row["evidence_refs_json"], []),
            "confidence": row["confidence"],
            "status": row["status"],
            "metadata": json_loads(row["metadata_json"], {}),
            "created_at": row["created_at"],
        }
