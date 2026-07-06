#!/usr/bin/env python3
"""Offgrid Minds Agent Control Center MVP.

Local-only web dashboard and SQLite API. This module is intentionally separate
from the existing Pi/headset application code.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("OGM_CONTROL_CENTER_DB", DATA_DIR / "control_center.sqlite3"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}:{uuid.uuid4().hex[:12]}"


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS missions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                target_pack TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'created',
                human_reviewer TEXT,
                coverage_goal TEXT,
                completion_criteria TEXT,
                allowed_source_types TEXT,
                approved_domains TEXT,
                download_budget TEXT,
                api_budget TEXT,
                storage_budget TEXT,
                time_budget TEXT,
                success_metrics TEXT,
                knowledge_objects_expected TEXT,
                required_citations TEXT,
                safety_requirements TEXT,
                cko_recommendation TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mission_events (
                id TEXT PRIMARY KEY,
                mission_id TEXT,
                event_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                actor TEXT NOT NULL DEFAULT 'human',
                created_at TEXT NOT NULL,
                FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS source_candidates (
                id TEXT PRIMARY KEY,
                mission_id TEXT,
                title TEXT NOT NULL,
                url_or_path TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'manual',
                source_class TEXT NOT NULL DEFAULT 'Unknown Source',
                quality_score REAL NOT NULL DEFAULT 0.4,
                license_status TEXT NOT NULL DEFAULT 'unknown',
                status TEXT NOT NULL DEFAULT 'candidate_found',
                relevance_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS source_reviews (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                reviewer TEXT NOT NULL DEFAULT 'human',
                quality_score REAL NOT NULL,
                source_class TEXT NOT NULL,
                license_status TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES source_candidates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS coverage_items (
                id TEXT PRIMARY KEY,
                pack_id TEXT NOT NULL,
                parent_id TEXT,
                name TEXT NOT NULL,
                current_percent REAL NOT NULL DEFAULT 0,
                target_percent REAL NOT NULL DEFAULT 95,
                status TEXT NOT NULL DEFAULT 'tracked',
                notes TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES coverage_items(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_debt (
                id TEXT PRIMARY KEY,
                pack_id TEXT NOT NULL,
                coverage_item_id TEXT,
                debt_type TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                recommended_action TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (coverage_item_id) REFERENCES coverage_items(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS agent_logs (
                id TEXT PRIMARY KEY,
                mission_id TEXT,
                agent_name TEXT NOT NULL DEFAULT 'CKO',
                log_type TEXT NOT NULL DEFAULT 'note',
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                approver TEXT NOT NULL DEFAULT 'human',
                reason TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        seed_defaults(conn)


def seed_defaults(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) AS count FROM coverage_items").fetchone()["count"]
    if existing:
        return

    timestamp = now_iso()
    pack_id = "ogm.pack.north-american-outdoor"
    root_id = "coverage:outdoor"
    coverage = [
        (root_id, pack_id, None, "North American Outdoor Expert Pack", 0, 90, "tracked"),
        ("coverage:outdoor:species", pack_id, root_id, "Species Identification", 0, 94, "tracked"),
        ("coverage:outdoor:trees", pack_id, "coverage:outdoor:species", "Trees", 0, 98, "tracked"),
        ("coverage:outdoor:mushrooms", pack_id, "coverage:outdoor:species", "Mushrooms", 0, 95, "tracked"),
        ("coverage:outdoor:navigation", pack_id, root_id, "Navigation", 0, 95, "tracked"),
        ("coverage:outdoor:wilderness-medicine", pack_id, root_id, "Wilderness Medicine", 0, 95, "tracked"),
        ("coverage:outdoor:weather", pack_id, root_id, "Weather", 0, 95, "tracked"),
    ]
    conn.executemany(
        """
        INSERT INTO coverage_items
            (id, pack_id, parent_id, name, current_percent, target_percent, status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(*row, timestamp) for row in coverage],
    )
    conn.execute(
        """
        INSERT INTO knowledge_debt
            (id, pack_id, coverage_item_id, debt_type, severity, description, status, recommended_action, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "debt:outdoor:navigation:bootstrap",
            pack_id,
            "coverage:outdoor:navigation",
            "low_coverage",
            "high",
            "Navigation coverage needs authoritative USGS, NOAA, map, compass, and emergency decision-tree sources.",
            "open",
            "Create a mission for navigation and emergency basics sources.",
            timestamp,
            timestamp,
        ),
    )
    conn.execute(
        """
        INSERT INTO agent_logs (id, mission_id, agent_name, log_type, message, created_at)
        VALUES (?, NULL, 'CKO', 'cko_recommendation', ?, ?)
        """,
        (
            "log:cko:bootstrap",
            "Draft the first North American Outdoor mission around navigation and emergency basics before broad species coverage.",
            timestamp,
        ),
    )


def create_event(conn: sqlite3.Connection, mission_id: str | None, event_type: str, summary: str, actor: str = "human") -> None:
    conn.execute(
        """
        INSERT INTO mission_events (id, mission_id, event_type, summary, actor, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (new_id("evt"), mission_id, event_type, summary, actor, now_iso()),
    )


def create_approval(
    conn: sqlite3.Connection,
    target_type: str,
    target_id: str,
    decision: str,
    approver: str,
    reason: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO approvals (id, target_type, target_id, decision, approver, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (new_id("approval"), target_type, target_id, decision, approver or "human", reason, now_iso()),
    )


class ControlCenterHandler(SimpleHTTPRequestHandler):
    server_version = "OGMControlCenter/0.1"

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            self.handle_api_get(path, parse_qs(parsed.query))
            return
        self.serve_static(path)

    def do_POST(self) -> None:
        self.handle_mutation("POST")

    def do_PATCH(self) -> None:
        self.handle_mutation("PATCH")

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_json(self, payload: object, status: int = 200) -> None:
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"error": message}, status)

    def serve_static(self, path: str) -> None:
        if path in {"/", ""}:
            file_path = STATIC_DIR / "index.html"
        elif path.startswith("/static/"):
            file_path = STATIC_DIR / path.removeprefix("/static/")
        else:
            file_path = STATIC_DIR / "index.html"

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return

        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_api_get(self, path: str, query: dict[str, list[str]]) -> None:
        with connect() as conn:
            if path == "/api/dashboard":
                self.send_json(get_dashboard(conn))
            elif path == "/api/missions":
                self.send_json(rows_to_dicts(conn.execute("SELECT * FROM missions ORDER BY created_at DESC").fetchall()))
            elif path.startswith("/api/missions/"):
                mission_id = path.split("/")[-1]
                mission = conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
                if not mission:
                    self.send_error_json(404, "Mission not found")
                    return
                self.send_json(dict(mission))
            elif path == "/api/mission_events":
                mission_id = query.get("mission_id", [None])[0]
                sql = "SELECT * FROM mission_events"
                args: tuple = ()
                if mission_id:
                    sql += " WHERE mission_id = ?"
                    args = (mission_id,)
                sql += " ORDER BY created_at DESC LIMIT 200"
                self.send_json(rows_to_dicts(conn.execute(sql, args).fetchall()))
            elif path == "/api/source_candidates":
                mission_id = query.get("mission_id", [None])[0]
                sql = "SELECT * FROM source_candidates"
                args = ()
                if mission_id:
                    sql += " WHERE mission_id = ?"
                    args = (mission_id,)
                sql += " ORDER BY created_at DESC"
                self.send_json(rows_to_dicts(conn.execute(sql, args).fetchall()))
            elif path == "/api/source_reviews":
                self.send_json(rows_to_dicts(conn.execute("SELECT * FROM source_reviews ORDER BY created_at DESC").fetchall()))
            elif path == "/api/coverage_items":
                self.send_json(rows_to_dicts(conn.execute("SELECT * FROM coverage_items ORDER BY pack_id, name").fetchall()))
            elif path == "/api/knowledge_debt":
                self.send_json(rows_to_dicts(conn.execute("SELECT * FROM knowledge_debt ORDER BY created_at DESC").fetchall()))
            elif path == "/api/agent_logs":
                self.send_json(rows_to_dicts(conn.execute("SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT 200").fetchall()))
            elif path == "/api/approvals":
                self.send_json(rows_to_dicts(conn.execute("SELECT * FROM approvals ORDER BY created_at DESC LIMIT 200").fetchall()))
            elif path == "/api/settings":
                self.send_json(
                    {
                        "database_path": str(DB_PATH),
                        "module_root": str(ROOT),
                        "autonomous_crawling": False,
                        "autonomous_publishing": False,
                        "expert_pack_compilation": False,
                        "human_approval_required": True,
                    }
                )
            else:
                self.send_error_json(404, "Unknown API endpoint")

    def handle_mutation(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith("/api/"):
            self.send_error_json(404, "Unknown endpoint")
            return
        try:
            data = self.read_json()
            with connect() as conn:
                if method == "POST" and path == "/api/missions":
                    self.send_json(create_mission(conn, data), 201)
                elif method == "PATCH" and path.startswith("/api/missions/"):
                    mission_id = path.split("/")[-1]
                    self.send_json(update_mission(conn, mission_id, data))
                elif method == "POST" and path == "/api/source_candidates":
                    self.send_json(create_source_candidate(conn, data), 201)
                elif method == "POST" and path.endswith("/review") and path.startswith("/api/source_candidates/"):
                    source_id = path.split("/")[-2]
                    self.send_json(review_source(conn, source_id, data), 201)
                elif method == "POST" and path == "/api/coverage_items":
                    self.send_json(create_coverage_item(conn, data), 201)
                elif method == "PATCH" and path.startswith("/api/coverage_items/"):
                    item_id = path.split("/")[-1]
                    self.send_json(update_simple(conn, "coverage_items", item_id, data, {"name", "current_percent", "target_percent", "status", "notes"}))
                elif method == "POST" and path == "/api/knowledge_debt":
                    self.send_json(create_debt_item(conn, data), 201)
                elif method == "PATCH" and path.startswith("/api/knowledge_debt/"):
                    debt_id = path.split("/")[-1]
                    self.send_json(update_simple(conn, "knowledge_debt", debt_id, data, {"severity", "description", "status", "recommended_action"}))
                elif method == "POST" and path == "/api/agent_logs":
                    self.send_json(create_agent_log(conn, data), 201)
                else:
                    self.send_error_json(404, "Unknown API endpoint")
        except ValueError as exc:
            self.send_error_json(400, str(exc))
        except sqlite3.IntegrityError as exc:
            self.send_error_json(400, f"Database constraint failed: {exc}")
        except json.JSONDecodeError:
            self.send_error_json(400, "Invalid JSON")


def get_dashboard(conn: sqlite3.Connection) -> dict:
    def count(table: str, where: str = "1 = 1") -> int:
        return conn.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE {where}").fetchone()["count"]

    return {
        "counts": {
            "missions": count("missions"),
            "active_missions": count("missions", "status NOT IN ('published', 'cancelled')"),
            "source_candidates": count("source_candidates"),
            "pending_sources": count("source_candidates", "status IN ('candidate_found', 'pending_review')"),
            "approved_sources": count("source_candidates", "status = 'approved'"),
            "rejected_sources": count("source_candidates", "status = 'rejected'"),
            "knowledge_debt_open": count("knowledge_debt", "status != 'resolved'"),
            "coverage_items": count("coverage_items"),
        },
        "recent_events": rows_to_dicts(
            conn.execute("SELECT * FROM mission_events ORDER BY created_at DESC LIMIT 10").fetchall()
        ),
        "cko_recommendations": rows_to_dicts(
            conn.execute(
                "SELECT * FROM agent_logs WHERE log_type = 'cko_recommendation' ORDER BY created_at DESC LIMIT 5"
            ).fetchall()
        ),
    }


def create_mission(conn: sqlite3.Connection, data: dict) -> dict:
    name = require(data, "name")
    target_pack = require(data, "target_pack")
    mission_id = data.get("id") or new_id("mission")
    timestamp = now_iso()
    fields = {
        "id": mission_id,
        "name": name,
        "target_pack": target_pack,
        "priority": data.get("priority", "medium"),
        "status": data.get("status", "created"),
        "human_reviewer": data.get("human_reviewer", ""),
        "coverage_goal": data.get("coverage_goal", ""),
        "completion_criteria": data.get("completion_criteria", ""),
        "allowed_source_types": data.get("allowed_source_types", ""),
        "approved_domains": data.get("approved_domains", ""),
        "download_budget": data.get("download_budget", ""),
        "api_budget": data.get("api_budget", ""),
        "storage_budget": data.get("storage_budget", ""),
        "time_budget": data.get("time_budget", ""),
        "success_metrics": data.get("success_metrics", ""),
        "knowledge_objects_expected": data.get("knowledge_objects_expected", ""),
        "required_citations": data.get("required_citations", ""),
        "safety_requirements": data.get("safety_requirements", ""),
        "cko_recommendation": data.get("cko_recommendation", ""),
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    conn.execute(
        f"INSERT INTO missions ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})",
        tuple(fields.values()),
    )
    create_event(conn, mission_id, "mission_created", f"Mission created: {name}")
    create_approval(conn, "mission", mission_id, "created", "human", "Mission record created; approval required before autonomous work.")
    return dict(conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone())


def update_mission(conn: sqlite3.Connection, mission_id: str, data: dict) -> dict:
    existing = conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
    if not existing:
        raise ValueError("Mission not found")
    allowed = {
        "name",
        "target_pack",
        "priority",
        "status",
        "human_reviewer",
        "coverage_goal",
        "completion_criteria",
        "allowed_source_types",
        "approved_domains",
        "download_budget",
        "api_budget",
        "storage_budget",
        "time_budget",
        "success_metrics",
        "knowledge_objects_expected",
        "required_citations",
        "safety_requirements",
        "cko_recommendation",
    }
    update = {key: data[key] for key in allowed if key in data}
    if not update:
        return dict(existing)
    update["updated_at"] = now_iso()
    assignments = ", ".join(f"{key} = ?" for key in update)
    conn.execute(f"UPDATE missions SET {assignments} WHERE id = ?", (*update.values(), mission_id))
    if "status" in update and update["status"] != existing["status"]:
        create_event(conn, mission_id, "mission_status_changed", f"Mission status changed from {existing['status']} to {update['status']}")
        create_approval(conn, "mission", mission_id, update["status"], data.get("approver", "human"), data.get("reason", "Human-updated mission status."))
    return dict(conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone())


def create_source_candidate(conn: sqlite3.Connection, data: dict) -> dict:
    title = require(data, "title")
    url_or_path = require(data, "url_or_path")
    timestamp = now_iso()
    source_id = data.get("id") or new_id("src")
    fields = {
        "id": source_id,
        "mission_id": data.get("mission_id") or None,
        "title": title,
        "url_or_path": url_or_path,
        "source_type": data.get("source_type", "manual"),
        "source_class": data.get("source_class", "Unknown Source"),
        "quality_score": float(data.get("quality_score", 0.4)),
        "license_status": data.get("license_status", "unknown"),
        "status": "candidate_found",
        "relevance_notes": data.get("relevance_notes", ""),
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    conn.execute(
        f"INSERT INTO source_candidates ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})",
        tuple(fields.values()),
    )
    create_event(conn, fields["mission_id"], "source_found", f"Source candidate added: {title}")
    return dict(conn.execute("SELECT * FROM source_candidates WHERE id = ?", (source_id,)).fetchone())


def review_source(conn: sqlite3.Connection, source_id: str, data: dict) -> dict:
    source = conn.execute("SELECT * FROM source_candidates WHERE id = ?", (source_id,)).fetchone()
    if not source:
        raise ValueError("Source candidate not found")

    decision = require(data, "decision")
    if decision not in {"approved", "rejected"}:
        raise ValueError("Decision must be approved or rejected")

    timestamp = now_iso()
    quality_score = float(data.get("quality_score", source["quality_score"]))
    source_class = data.get("source_class", source["source_class"])
    license_status = data.get("license_status", source["license_status"])
    notes = data.get("notes", "")
    reviewer = data.get("reviewer", "human")

    conn.execute(
        """
        INSERT INTO source_reviews
            (id, source_id, decision, reviewer, quality_score, source_class, license_status, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (new_id("review"), source_id, decision, reviewer, quality_score, source_class, license_status, notes, timestamp),
    )
    conn.execute(
        """
        UPDATE source_candidates
        SET status = ?, quality_score = ?, source_class = ?, license_status = ?, updated_at = ?
        WHERE id = ?
        """,
        (decision, quality_score, source_class, license_status, timestamp, source_id),
    )
    create_approval(conn, "source", source_id, decision, reviewer, notes)
    create_event(conn, source["mission_id"], f"source_{decision}", f"Source {decision}: {source['title']}")
    return dict(conn.execute("SELECT * FROM source_candidates WHERE id = ?", (source_id,)).fetchone())


def create_coverage_item(conn: sqlite3.Connection, data: dict) -> dict:
    item_id = data.get("id") or new_id("coverage")
    timestamp = now_iso()
    fields = {
        "id": item_id,
        "pack_id": require(data, "pack_id"),
        "parent_id": data.get("parent_id") or None,
        "name": require(data, "name"),
        "current_percent": float(data.get("current_percent", 0)),
        "target_percent": float(data.get("target_percent", 95)),
        "status": data.get("status", "tracked"),
        "notes": data.get("notes", ""),
        "updated_at": timestamp,
    }
    conn.execute(
        f"INSERT INTO coverage_items ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})",
        tuple(fields.values()),
    )
    create_event(conn, None, "coverage_item_created", f"Coverage item created: {fields['name']}", "human")
    return dict(conn.execute("SELECT * FROM coverage_items WHERE id = ?", (item_id,)).fetchone())


def create_debt_item(conn: sqlite3.Connection, data: dict) -> dict:
    debt_id = data.get("id") or new_id("debt")
    timestamp = now_iso()
    fields = {
        "id": debt_id,
        "pack_id": require(data, "pack_id"),
        "coverage_item_id": data.get("coverage_item_id") or None,
        "debt_type": require(data, "debt_type"),
        "severity": data.get("severity", "medium"),
        "description": require(data, "description"),
        "status": data.get("status", "open"),
        "recommended_action": data.get("recommended_action", ""),
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    conn.execute(
        f"INSERT INTO knowledge_debt ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})",
        tuple(fields.values()),
    )
    create_event(conn, None, "knowledge_debt_created", f"Knowledge Debt created: {fields['description'][:80]}", "human")
    return dict(conn.execute("SELECT * FROM knowledge_debt WHERE id = ?", (debt_id,)).fetchone())


def create_agent_log(conn: sqlite3.Connection, data: dict) -> dict:
    log_id = data.get("id") or new_id("log")
    fields = {
        "id": log_id,
        "mission_id": data.get("mission_id") or None,
        "agent_name": data.get("agent_name", "CKO"),
        "log_type": data.get("log_type", "note"),
        "message": require(data, "message"),
        "created_at": now_iso(),
    }
    conn.execute(
        f"INSERT INTO agent_logs ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})",
        tuple(fields.values()),
    )
    create_event(conn, fields["mission_id"], "agent_log_created", f"{fields['agent_name']} log added: {fields['message'][:80]}", fields["agent_name"])
    return dict(conn.execute("SELECT * FROM agent_logs WHERE id = ?", (log_id,)).fetchone())


def update_simple(conn: sqlite3.Connection, table: str, row_id: str, data: dict, allowed: set[str]) -> dict:
    existing = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if not existing:
        raise ValueError("Record not found")
    update = {key: data[key] for key in allowed if key in data}
    if not update:
        return dict(existing)
    if "updated_at" in existing.keys():
        update["updated_at"] = now_iso()
    assignments = ", ".join(f"{key} = ?" for key in update)
    conn.execute(f"UPDATE {table} SET {assignments} WHERE id = ?", (*update.values(), row_id))
    create_event(conn, None, f"{table}_updated", f"{table} updated: {row_id}", data.get("actor", "human"))
    return dict(conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone())


def require(data: dict, key: str) -> str:
    value = data.get(key)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing required field: {key}")
    return str(value).strip()


def main() -> None:
    init_db()
    port = int(os.environ.get("OGM_CONTROL_CENTER_PORT", "8787"))
    address = ("127.0.0.1", port)
    print(f"Offgrid Minds Agent Control Center")
    print(f"Dashboard: http://{address[0]}:{address[1]}")
    print(f"Database:  {DB_PATH}")
    ThreadingHTTPServer(address, ControlCenterHandler).serve_forever()


if __name__ == "__main__":
    main()
