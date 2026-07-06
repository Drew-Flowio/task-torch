from __future__ import annotations

import argparse
import html
import os
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse


APP_NAME = "Offgrid Minds Agent Control Center"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "control_center.db"

MISSION_STATUSES = [
    "created",
    "awaiting_approval",
    "approved",
    "research",
    "source_vetting",
    "acquisition",
    "ocr",
    "knowledge_engineering",
    "indexing",
    "validation",
    "compilation",
    "human_review",
    "published",
    "coverage_updated",
    "debt_updated",
    "blocked",
    "paused",
    "cancelled",
]

MISSION_PRIORITIES = ["critical", "high", "medium", "low", "backlog"]
SOURCE_STATUSES = [
    "candidate_found",
    "pending_vetting",
    "vetted_pending_human",
    "approved_for_intake",
    "approved_local_only",
    "rejected",
    "needs_license_review",
    "intaked",
    "quarantined",
]
SOURCE_CLASSES = [
    "Official Manufacturer",
    "Government",
    "University",
    "Professional Organization",
    "Industry Standard",
    "Commercial Manual",
    "Public Domain Book",
    "Community Source",
    "Unknown Source",
]
DEBT_STATUSES = ["open", "assigned", "in_progress", "resolved", "accepted_risk"]
DEBT_TYPES = [
    "missing_diagram",
    "missing_procedure",
    "conflicting_manuals",
    "low_ocr_confidence",
    "unknown_copyright",
    "low_quality_source",
    "missing_citation",
    "missing_image",
    "missing_entity",
    "weak_relationships",
    "outdated_source",
    "insufficient_human_review",
    "failed_retrieval_test",
    "safety_review_needed",
    "low_coverage",
    "poor_localization",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def db_connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_name TEXT NOT NULL,
    target_expert_pack TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'created',
    human_reviewer TEXT NOT NULL DEFAULT '',
    required_deliverables TEXT NOT NULL DEFAULT '',
    coverage_goal TEXT NOT NULL DEFAULT '',
    completion_criteria TEXT NOT NULL DEFAULT '',
    allowed_source_types TEXT NOT NULL DEFAULT '',
    approved_domains TEXT NOT NULL DEFAULT '',
    download_budget TEXT NOT NULL DEFAULT '',
    api_budget TEXT NOT NULL DEFAULT '',
    storage_budget TEXT NOT NULL DEFAULT '',
    time_budget TEXT NOT NULL DEFAULT '',
    success_metrics TEXT NOT NULL DEFAULT '',
    knowledge_objects_expected TEXT NOT NULL DEFAULT '',
    required_citations TEXT NOT NULL DEFAULT '',
    safety_requirements TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mission_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id INTEGER,
    event_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'human',
    before_state TEXT,
    after_state TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS source_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    url_or_path TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT '',
    source_class TEXT NOT NULL DEFAULT 'Unknown Source',
    status TEXT NOT NULL DEFAULT 'candidate_found',
    quality_score REAL NOT NULL DEFAULT 0.0,
    quality_confidence REAL NOT NULL DEFAULT 0.0,
    license_state TEXT NOT NULL DEFAULT 'unknown',
    relevance_score REAL NOT NULL DEFAULT 0.0,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS source_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    decision TEXT NOT NULL,
    reviewer TEXT NOT NULL DEFAULT 'human',
    reliability_notes TEXT NOT NULL DEFAULT '',
    license_notes TEXT NOT NULL DEFAULT '',
    allowed_use TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES source_candidates(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS coverage_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_id TEXT NOT NULL,
    parent_id INTEGER,
    name TEXT NOT NULL,
    domain_path TEXT NOT NULL DEFAULT '',
    target_percent REAL NOT NULL DEFAULT 100.0,
    current_percent REAL NOT NULL DEFAULT 0.0,
    measurement_method TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES coverage_items(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS knowledge_debt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_id TEXT NOT NULL,
    coverage_item_id INTEGER,
    debt_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'open',
    description TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (coverage_item_id) REFERENCES coverage_items(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS agent_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id INTEGER,
    agent_name TEXT NOT NULL DEFAULT 'CKO',
    log_level TEXT NOT NULL DEFAULT 'info',
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    decision TEXT NOT NULL,
    approver TEXT NOT NULL DEFAULT 'human',
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cko_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id INTEGER,
    recommendation_type TEXT NOT NULL DEFAULT 'future_work',
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'medium',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE SET NULL
);
"""


def init_db(db_path: Path) -> None:
    with db_connect(db_path) as conn:
        conn.executescript(SCHEMA)
        seed_if_empty(conn)


def seed_if_empty(conn: sqlite3.Connection) -> None:
    mission_count = conn.execute("SELECT COUNT(*) FROM missions").fetchone()[0]
    now = utc_now()
    if mission_count == 0:
        cur = conn.execute(
            """
            INSERT INTO missions (
                mission_name, target_expert_pack, priority, status, human_reviewer,
                required_deliverables, coverage_goal, completion_criteria,
                allowed_source_types, approved_domains, download_budget, api_budget,
                storage_budget, time_budget, success_metrics, knowledge_objects_expected,
                required_citations, safety_requirements, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "North American Outdoor MVP: navigation and emergency basics",
                "ogm.pack.north-american-outdoor",
                "high",
                "created",
                "Outdoor Lead Reviewer",
                "Approved sources, cited Knowledge Object candidates, coverage/debt baseline",
                "Navigation and emergency basics reach production-quality readiness",
                "All sources approved; citations present; remaining debt documented",
                "Government Publication, Professional Field Guide, Technical Standard, Public Domain Book",
                "usgs.gov, noaa.gov, nps.gov, fs.usda.gov",
                "50 files / 10 GB",
                "1,000 requests",
                "50 GB working storage",
                "14 days",
                "citation quality >= 0.95; source quality >= 0.85",
                "50 procedures, 25 decision-tree objects, 25 reference objects",
                "minimum 1 per object; 2 for safety-critical procedures",
                "Human review required for wilderness medicine and emergency guidance",
                now,
                now,
            ),
        )
        mission_id = cur.lastrowid
        conn.execute(
            """
            INSERT INTO mission_events (mission_id, event_type, summary, actor, after_state, created_at)
            VALUES (?, 'mission_created', 'Seed mission created for the flagship Outdoor MVP.', 'system', 'created', ?)
            """,
            (mission_id, now),
        )
        conn.execute(
            """
            INSERT INTO cko_recommendations (
                mission_id, recommendation_type, title, body, status, priority, created_at, updated_at
            ) VALUES (?, 'mvp_focus', ?, ?, 'open', 'high', ?, ?)
            """,
            (
                mission_id,
                "Keep the first MVP narrow",
                "Start with navigation and emergency basics before broad species coverage. This proves mission control, source approval, coverage, debt, and audit workflows without needing autonomous agents.",
                now,
                now,
            ),
        )

    coverage_count = conn.execute("SELECT COUNT(*) FROM coverage_items").fetchone()[0]
    if coverage_count == 0:
        pack = "ogm.pack.north-american-outdoor"
        rows = [
            (pack, None, "North American Outdoor Expert Pack", "outdoor", 85, 8, "manual baseline"),
            (pack, 1, "Navigation", "outdoor/navigation", 95, 12, "manual baseline"),
            (pack, 1, "Emergency Medicine", "outdoor/emergency_medicine", 90, 5, "manual baseline"),
            (pack, 1, "Weather", "outdoor/weather", 90, 10, "manual baseline"),
            (pack, 1, "Field Knots", "outdoor/field_knots", 85, 6, "manual baseline"),
        ]
        for pack_id, parent_id, name, path, target, current, method in rows:
            conn.execute(
                """
                INSERT INTO coverage_items (
                    pack_id, parent_id, name, domain_path, target_percent,
                    current_percent, measurement_method, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (pack_id, parent_id, name, path, target, current, method, now),
            )

    debt_count = conn.execute("SELECT COUNT(*) FROM knowledge_debt").fetchone()[0]
    if debt_count == 0:
        conn.execute(
            """
            INSERT INTO knowledge_debt (
                pack_id, coverage_item_id, debt_type, severity, status,
                description, evidence, recommended_action, created_at, updated_at
            ) VALUES (?, 2, 'low_coverage', 'high', 'open', ?, ?, ?, ?, ?)
            """,
            (
                "ogm.pack.north-american-outdoor",
                "Navigation coverage is below the target for the flagship MVP.",
                "Initial coverage baseline shows 12% current coverage against a 95% target.",
                "Create approved source missions for USGS map references and NOAA navigation/weather material.",
                now,
                now,
            ),
        )


class Repository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        return db_connect(self.db_path)

    def audit(
        self,
        conn: sqlite3.Connection,
        *,
        mission_id: int | None,
        event_type: str,
        summary: str,
        actor: str = "human",
        before_state: str | None = None,
        after_state: str | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO mission_events (
                mission_id, event_type, summary, actor, before_state, after_state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (mission_id, event_type, summary, actor, before_state, after_state, utc_now()),
        )

    def log(
        self,
        conn: sqlite3.Connection,
        *,
        mission_id: int | None,
        agent_name: str,
        message: str,
        level: str = "info",
    ) -> None:
        conn.execute(
            """
            INSERT INTO agent_logs (mission_id, agent_name, log_level, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (mission_id, agent_name, level, message, utc_now()),
        )


def fetch_stats(repo: Repository) -> dict[str, Any]:
    with repo.connect() as conn:
        return {
            "missions": conn.execute("SELECT COUNT(*) FROM missions").fetchone()[0],
            "active_missions": conn.execute(
                "SELECT COUNT(*) FROM missions WHERE status NOT IN ('published', 'cancelled')"
            ).fetchone()[0],
            "pending_sources": conn.execute(
                "SELECT COUNT(*) FROM source_candidates WHERE status IN ('candidate_found', 'pending_vetting', 'vetted_pending_human', 'needs_license_review')"
            ).fetchone()[0],
            "approved_sources": conn.execute(
                "SELECT COUNT(*) FROM source_candidates WHERE status IN ('approved_for_intake', 'approved_local_only', 'intaked')"
            ).fetchone()[0],
            "open_debt": conn.execute(
                "SELECT COUNT(*) FROM knowledge_debt WHERE status NOT IN ('resolved', 'accepted_risk')"
            ).fetchone()[0],
            "coverage_avg": conn.execute("SELECT AVG(current_percent) FROM coverage_items").fetchone()[0] or 0,
            "recommendations": conn.execute(
                "SELECT COUNT(*) FROM cko_recommendations WHERE status = 'open'"
            ).fetchone()[0],
        }


def layout(title: str, body: str, active: str = "") -> bytes:
    nav_items = [
        ("/", "Dashboard", "dashboard"),
        ("/missions", "Missions", "missions"),
        ("/source-review", "Source Review", "sources"),
        ("/coverage", "Coverage", "coverage"),
        ("/knowledge-debt", "Knowledge Debt", "debt"),
        ("/logs", "Logs / Audit", "logs"),
        ("/settings", "Settings", "settings"),
    ]
    nav = "".join(
        f'<a class="{"active" if key == active else ""}" href="{href}">{label}</a>'
        for href, label, key in nav_items
    )
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} - {APP_NAME}</title>
  <style>
    :root {{
      --bg: #0e1116;
      --panel: #171c24;
      --panel-2: #202735;
      --text: #edf2f7;
      --muted: #9aa7b8;
      --line: #2f3a4b;
      --accent: #7dd3fc;
      --good: #8bd99f;
      --warn: #ffd166;
      --bad: #ff8a8a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding: 18px 24px;
      background: #111722;
    }}
    header h1 {{ margin: 0; font-size: 20px; letter-spacing: 0.02em; }}
    header p {{ margin: 6px 0 0; color: var(--muted); }}
    nav {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      padding: 12px 24px;
      border-bottom: 1px solid var(--line);
      background: #121821;
    }}
    nav a {{
      color: var(--muted);
      text-decoration: none;
      padding: 8px 10px;
      border-radius: 8px;
    }}
    nav a.active, nav a:hover {{ background: var(--panel-2); color: var(--text); }}
    main {{ padding: 24px; max-width: 1280px; margin: 0 auto; }}
    .grid {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.18);
    }}
    .card h2, .card h3 {{ margin-top: 0; }}
    .metric {{ font-size: 34px; font-weight: 700; color: var(--accent); }}
    .muted {{ color: var(--muted); }}
    .row {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: end; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 10px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    input, select, textarea {{
      width: 100%;
      background: #0f141d;
      border: 1px solid var(--line);
      color: var(--text);
      border-radius: 8px;
      padding: 9px;
      font: inherit;
    }}
    textarea {{ min-height: 88px; }}
    label {{ display: block; color: var(--muted); margin-bottom: 6px; font-size: 13px; }}
    .field {{ flex: 1 1 220px; margin-bottom: 12px; }}
    button, .button {{
      background: var(--accent);
      color: #071019;
      border: 0;
      border-radius: 8px;
      padding: 9px 12px;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
      display: inline-block;
    }}
    .button.secondary, button.secondary {{ background: var(--panel-2); color: var(--text); border: 1px solid var(--line); }}
    .pill {{
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      color: var(--muted);
      font-size: 12px;
    }}
    .pill.good {{ color: var(--good); border-color: rgba(139,217,159,.5); }}
    .pill.warn {{ color: var(--warn); border-color: rgba(255,209,102,.5); }}
    .pill.bad {{ color: var(--bad); border-color: rgba(255,138,138,.5); }}
    .split {{ display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(280px, .6fr); gap: 16px; }}
    @media (max-width: 900px) {{ .split {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{APP_NAME}</h1>
    <p>Local Mission Control MVP. No crawling, no autonomous publishing, no pack compilation.</p>
  </header>
  <nav>{nav}</nav>
  <main>{body}</main>
</body>
</html>"""
    return html_doc.encode("utf-8")


def options(values: list[str], selected: str = "") -> str:
    return "".join(
        f'<option value="{esc(value)}" {"selected" if value == selected else ""}>{esc(value)}</option>'
        for value in values
    )


def status_pill(status: str) -> str:
    cls = "good" if status in {"approved", "published", "resolved", "approved_for_intake", "approved_local_only", "intaked"} else "bad" if status in {"rejected", "cancelled", "blocked", "quarantined"} else "warn"
    return f'<span class="pill {cls}">{esc(status)}</span>'


def dashboard_page(repo: Repository) -> bytes:
    stats = fetch_stats(repo)
    with repo.connect() as conn:
        missions = conn.execute(
            "SELECT * FROM missions ORDER BY updated_at DESC LIMIT 6"
        ).fetchall()
        recs = conn.execute(
            "SELECT r.*, m.mission_name FROM cko_recommendations r LEFT JOIN missions m ON m.id = r.mission_id ORDER BY r.updated_at DESC LIMIT 6"
        ).fetchall()
        events = conn.execute(
            "SELECT e.*, m.mission_name FROM mission_events e LEFT JOIN missions m ON m.id = e.mission_id ORDER BY e.created_at DESC LIMIT 8"
        ).fetchall()

    metrics = "".join(
        f"""
        <div class="card">
          <div class="metric">{esc(value)}</div>
          <div class="muted">{esc(label)}</div>
        </div>
        """
        for label, value in [
            ("Missions", stats["missions"]),
            ("Active Missions", stats["active_missions"]),
            ("Pending Sources", stats["pending_sources"]),
            ("Approved Sources", stats["approved_sources"]),
            ("Open Knowledge Debt", stats["open_debt"]),
            ("Avg Coverage", f"{stats['coverage_avg']:.1f}%"),
            ("Open CKO Recommendations", stats["recommendations"]),
        ]
    )
    mission_rows = "".join(
        f"""
        <tr>
          <td><a class="button secondary" href="/missions/{row['id']}">Open</a></td>
          <td>{esc(row['mission_name'])}</td>
          <td>{esc(row['target_expert_pack'])}</td>
          <td>{status_pill(row['status'])}</td>
          <td>{esc(row['priority'])}</td>
        </tr>
        """
        for row in missions
    )
    rec_rows = "".join(
        f"""
        <tr>
          <td>{esc(row['title'])}<br><span class="muted">{esc(row['body'])}</span></td>
          <td>{esc(row['mission_name'] or 'General')}</td>
          <td>{status_pill(row['status'])}</td>
        </tr>
        """
        for row in recs
    )
    event_rows = "".join(
        f"""
        <tr>
          <td>{esc(row['created_at'])}</td>
          <td>{esc(row['event_type'])}</td>
          <td>{esc(row['mission_name'] or 'No mission')}</td>
          <td>{esc(row['summary'])}</td>
        </tr>
        """
        for row in events
    )
    body = f"""
    <section class="grid">{metrics}</section>
    <section class="split" style="margin-top:16px;">
      <div class="card">
        <h2>Recent Missions</h2>
        <table><thead><tr><th></th><th>Name</th><th>Pack</th><th>Status</th><th>Priority</th></tr></thead><tbody>{mission_rows}</tbody></table>
      </div>
      <div class="card">
        <h2>Manual CKO Recommendation</h2>
        <form method="post" action="/recommendations/create">
          <div class="field"><label>Title</label><input name="title" required></div>
          <div class="field"><label>Recommendation</label><textarea name="body" required></textarea></div>
          <div class="row">
            <div class="field"><label>Priority</label><select name="priority">{options(MISSION_PRIORITIES, 'medium')}</select></div>
            <div class="field"><label>Type</label><input name="recommendation_type" value="future_work"></div>
          </div>
          <button type="submit">Add Recommendation</button>
        </form>
      </div>
    </section>
    <section class="card" style="margin-top:16px;">
      <h2>CKO Recommendations</h2>
      <table><thead><tr><th>Recommendation</th><th>Mission</th><th>Status</th></tr></thead><tbody>{rec_rows}</tbody></table>
    </section>
    <section class="card" style="margin-top:16px;">
      <h2>Audit Trail</h2>
      <table><thead><tr><th>Time</th><th>Event</th><th>Mission</th><th>Summary</th></tr></thead><tbody>{event_rows}</tbody></table>
    </section>
    """
    return layout("Dashboard", body, "dashboard")


def missions_page(repo: Repository) -> bytes:
    with repo.connect() as conn:
        missions = conn.execute("SELECT * FROM missions ORDER BY updated_at DESC").fetchall()
    rows = "".join(
        f"""
        <tr>
          <td><a class="button secondary" href="/missions/{row['id']}">Open</a></td>
          <td>{esc(row['mission_name'])}</td>
          <td>{esc(row['target_expert_pack'])}</td>
          <td>{status_pill(row['status'])}</td>
          <td>{esc(row['priority'])}</td>
          <td>{esc(row['human_reviewer'])}</td>
          <td>{esc(row['updated_at'])}</td>
        </tr>
        """
        for row in missions
    )
    body = f"""
    <section class="split">
      <div class="card">
        <h2>Missions</h2>
        <table>
          <thead><tr><th></th><th>Name</th><th>Pack</th><th>Status</th><th>Priority</th><th>Reviewer</th><th>Updated</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
      <div class="card">
        <h2>Create Mission</h2>
        <form method="post" action="/missions/create">
          <div class="field"><label>Mission Name</label><input name="mission_name" required></div>
          <div class="field"><label>Target Expert Pack</label><input name="target_expert_pack" value="ogm.pack.north-american-outdoor" required></div>
          <div class="row">
            <div class="field"><label>Priority</label><select name="priority">{options(MISSION_PRIORITIES, 'medium')}</select></div>
            <div class="field"><label>Status</label><select name="status">{options(MISSION_STATUSES, 'created')}</select></div>
          </div>
          <div class="field"><label>Human Reviewer</label><input name="human_reviewer" value="Human Reviewer"></div>
          <div class="field"><label>Required Deliverables</label><textarea name="required_deliverables"></textarea></div>
          <div class="field"><label>Coverage Goal</label><textarea name="coverage_goal"></textarea></div>
          <div class="field"><label>Completion Criteria</label><textarea name="completion_criteria"></textarea></div>
          <div class="field"><label>Allowed Source Types</label><textarea name="allowed_source_types"></textarea></div>
          <div class="field"><label>Approved Domains</label><textarea name="approved_domains"></textarea></div>
          <button type="submit">Create Mission</button>
        </form>
      </div>
    </section>
    """
    return layout("Missions", body, "missions")


def mission_detail_page(repo: Repository, mission_id: int) -> bytes:
    with repo.connect() as conn:
        mission = conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
        if mission is None:
            return not_found_page()
        sources = conn.execute(
            "SELECT * FROM source_candidates WHERE mission_id = ? ORDER BY updated_at DESC",
            (mission_id,),
        ).fetchall()
        events = conn.execute(
            "SELECT * FROM mission_events WHERE mission_id = ? ORDER BY created_at DESC LIMIT 30",
            (mission_id,),
        ).fetchall()
        logs = conn.execute(
            "SELECT * FROM agent_logs WHERE mission_id = ? ORDER BY created_at DESC LIMIT 20",
            (mission_id,),
        ).fetchall()
        recs = conn.execute(
            "SELECT * FROM cko_recommendations WHERE mission_id = ? ORDER BY updated_at DESC",
            (mission_id,),
        ).fetchall()
    source_rows = "".join(
        f"""
        <tr>
          <td>{esc(row['title'])}<br><span class="muted">{esc(row['url_or_path'])}</span></td>
          <td>{status_pill(row['status'])}</td>
          <td>{esc(row['source_class'])}</td>
          <td>{row['quality_score']:.2f}</td>
        </tr>
        """
        for row in sources
    )
    event_rows = "".join(
        f"<tr><td>{esc(row['created_at'])}</td><td>{esc(row['event_type'])}</td><td>{esc(row['summary'])}</td></tr>"
        for row in events
    )
    log_rows = "".join(
        f"<tr><td>{esc(row['created_at'])}</td><td>{esc(row['agent_name'])}</td><td>{esc(row['message'])}</td></tr>"
        for row in logs
    )
    rec_rows = "".join(
        f"<tr><td>{esc(row['title'])}<br><span class=\"muted\">{esc(row['body'])}</span></td><td>{status_pill(row['status'])}</td><td>{esc(row['priority'])}</td></tr>"
        for row in recs
    )
    body = f"""
    <section class="split">
      <div class="card">
        <h2>{esc(mission['mission_name'])}</h2>
        <p class="muted">Target pack: {esc(mission['target_expert_pack'])}</p>
        <div class="row">
          <span>{status_pill(mission['status'])}</span>
          <span class="pill">Priority: {esc(mission['priority'])}</span>
          <span class="pill">Reviewer: {esc(mission['human_reviewer'])}</span>
        </div>
        <h3>Mission Contract</h3>
        <table>
          <tr><th>Required Deliverables</th><td>{esc(mission['required_deliverables'])}</td></tr>
          <tr><th>Coverage Goal</th><td>{esc(mission['coverage_goal'])}</td></tr>
          <tr><th>Completion Criteria</th><td>{esc(mission['completion_criteria'])}</td></tr>
          <tr><th>Allowed Source Types</th><td>{esc(mission['allowed_source_types'])}</td></tr>
          <tr><th>Approved Domains</th><td>{esc(mission['approved_domains'])}</td></tr>
          <tr><th>Safety Requirements</th><td>{esc(mission['safety_requirements'])}</td></tr>
        </table>
      </div>
      <div class="card">
        <h2>Edit Mission Status</h2>
        <form method="post" action="/missions/{mission_id}/status">
          <div class="field"><label>Status</label><select name="status">{options(MISSION_STATUSES, mission['status'])}</select></div>
          <div class="field"><label>Reason / Human Approval Note</label><textarea name="reason" required>Human decision recorded.</textarea></div>
          <button type="submit">Update Status</button>
        </form>
        <h2>Add Manual CKO Recommendation</h2>
        <form method="post" action="/recommendations/create">
          <input type="hidden" name="mission_id" value="{mission_id}">
          <div class="field"><label>Title</label><input name="title" required></div>
          <div class="field"><label>Recommendation</label><textarea name="body" required></textarea></div>
          <div class="field"><label>Priority</label><select name="priority">{options(MISSION_PRIORITIES, 'medium')}</select></div>
          <button type="submit">Add Recommendation</button>
        </form>
      </div>
    </section>
    <section class="split" style="margin-top:16px;">
      <div class="card">
        <h2>Add Source Candidate Manually</h2>
        <form method="post" action="/sources/create">
          <input type="hidden" name="mission_id" value="{mission_id}">
          <div class="field"><label>Title</label><input name="title" required></div>
          <div class="field"><label>URL or Local Path</label><input name="url_or_path" required></div>
          <div class="row">
            <div class="field"><label>Source Type</label><input name="source_type" placeholder="government_publication"></div>
            <div class="field"><label>Source Class</label><select name="source_class">{options(SOURCE_CLASSES, 'Government')}</select></div>
          </div>
          <div class="row">
            <div class="field"><label>Quality Score 0-1</label><input name="quality_score" value="0.85"></div>
            <div class="field"><label>Relevance Score 0-1</label><input name="relevance_score" value="0.80"></div>
          </div>
          <div class="field"><label>Notes</label><textarea name="notes"></textarea></div>
          <button type="submit">Add Source Candidate</button>
        </form>
      </div>
      <div class="card">
        <h2>CKO Recommendations</h2>
        <table><thead><tr><th>Recommendation</th><th>Status</th><th>Priority</th></tr></thead><tbody>{rec_rows}</tbody></table>
      </div>
    </section>
    <section class="card" style="margin-top:16px;">
      <h2>Sources</h2>
      <table><thead><tr><th>Source</th><th>Status</th><th>Class</th><th>Quality</th></tr></thead><tbody>{source_rows}</tbody></table>
    </section>
    <section class="split" style="margin-top:16px;">
      <div class="card"><h2>Mission Audit</h2><table><thead><tr><th>Time</th><th>Event</th><th>Summary</th></tr></thead><tbody>{event_rows}</tbody></table></div>
      <div class="card"><h2>Agent / CKO Logs</h2><table><thead><tr><th>Time</th><th>Actor</th><th>Message</th></tr></thead><tbody>{log_rows}</tbody></table></div>
    </section>
    """
    return layout("Mission Detail", body, "missions")


def source_review_page(repo: Repository) -> bytes:
    with repo.connect() as conn:
        sources = conn.execute(
            """
            SELECT s.*, m.mission_name FROM source_candidates s
            JOIN missions m ON m.id = s.mission_id
            ORDER BY s.updated_at DESC
            """
        ).fetchall()
        missions = conn.execute("SELECT id, mission_name FROM missions ORDER BY mission_name").fetchall()
    rows = "".join(
        f"""
        <tr>
          <td>{esc(row['title'])}<br><span class="muted">{esc(row['url_or_path'])}</span></td>
          <td>{esc(row['mission_name'])}</td>
          <td>{status_pill(row['status'])}</td>
          <td>{esc(row['source_class'])}<br><span class="muted">quality {row['quality_score']:.2f}, relevance {row['relevance_score']:.2f}</span></td>
          <td>
            <form method="post" action="/sources/{row['id']}/review">
              <div class="field"><label>Decision</label><select name="decision">
                <option value="approved_for_intake">Approve for intake</option>
                <option value="approved_local_only">Approve local-only</option>
                <option value="rejected">Reject</option>
                <option value="needs_license_review">Needs license review</option>
              </select></div>
              <div class="field"><label>Reason</label><textarea name="reason" required></textarea></div>
              <button type="submit">Record Human Review</button>
            </form>
          </td>
        </tr>
        """
        for row in sources
    )
    mission_options = "".join(
        f'<option value="{row["id"]}">{esc(row["mission_name"])}</option>' for row in missions
    )
    body = f"""
    <section class="split">
      <div class="card">
        <h2>Source Review</h2>
        <p class="muted">Manual source candidates only. No crawling is active in this MVP.</p>
        <table>
          <thead><tr><th>Source</th><th>Mission</th><th>Status</th><th>Quality</th><th>Human Review</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
      <div class="card">
        <h2>Add Source Candidate</h2>
        <form method="post" action="/sources/create">
          <div class="field"><label>Mission</label><select name="mission_id">{mission_options}</select></div>
          <div class="field"><label>Title</label><input name="title" required></div>
          <div class="field"><label>URL or Local Path</label><input name="url_or_path" required></div>
          <div class="field"><label>Source Type</label><input name="source_type"></div>
          <div class="field"><label>Source Class</label><select name="source_class">{options(SOURCE_CLASSES, 'Unknown Source')}</select></div>
          <div class="row">
            <div class="field"><label>Quality Score</label><input name="quality_score" value="0.50"></div>
            <div class="field"><label>Quality Confidence</label><input name="quality_confidence" value="0.50"></div>
          </div>
          <div class="field"><label>Notes</label><textarea name="notes"></textarea></div>
          <button type="submit">Add Candidate</button>
        </form>
      </div>
    </section>
    """
    return layout("Source Review", body, "sources")


def coverage_page(repo: Repository) -> bytes:
    with repo.connect() as conn:
        rows_db = conn.execute("SELECT * FROM coverage_items ORDER BY pack_id, domain_path, name").fetchall()
    rows = "".join(
        f"""
        <tr>
          <td>{esc(row['name'])}<br><span class="muted">{esc(row['domain_path'])}</span></td>
          <td>{esc(row['pack_id'])}</td>
          <td>{row['current_percent']:.1f}% / {row['target_percent']:.1f}%</td>
          <td>{esc(row['measurement_method'])}</td>
          <td>
            <form method="post" action="/coverage/{row['id']}/update" class="row">
              <div class="field"><label>Current %</label><input name="current_percent" value="{row['current_percent']:.1f}"></div>
              <div class="field"><label>Notes</label><input name="notes" value="{esc(row['notes'])}"></div>
              <button type="submit">Update</button>
            </form>
          </td>
        </tr>
        """
        for row in rows_db
    )
    body = f"""
    <section class="split">
      <div class="card">
        <h2>Coverage</h2>
        <table><thead><tr><th>Node</th><th>Pack</th><th>Coverage</th><th>Method</th><th>Update</th></tr></thead><tbody>{rows}</tbody></table>
      </div>
      <div class="card">
        <h2>Add Coverage Item</h2>
        <form method="post" action="/coverage/create">
          <div class="field"><label>Pack ID</label><input name="pack_id" value="ogm.pack.north-american-outdoor" required></div>
          <div class="field"><label>Name</label><input name="name" required></div>
          <div class="field"><label>Domain Path</label><input name="domain_path" placeholder="outdoor/navigation"></div>
          <div class="row">
            <div class="field"><label>Target %</label><input name="target_percent" value="95"></div>
            <div class="field"><label>Current %</label><input name="current_percent" value="0"></div>
          </div>
          <div class="field"><label>Measurement Method</label><input name="measurement_method" value="manual baseline"></div>
          <div class="field"><label>Notes</label><textarea name="notes"></textarea></div>
          <button type="submit">Add Coverage Item</button>
        </form>
      </div>
    </section>
    """
    return layout("Coverage", body, "coverage")


def knowledge_debt_page(repo: Repository) -> bytes:
    with repo.connect() as conn:
        debts = conn.execute(
            """
            SELECT d.*, c.name AS coverage_name FROM knowledge_debt d
            LEFT JOIN coverage_items c ON c.id = d.coverage_item_id
            ORDER BY CASE d.severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, d.updated_at DESC
            """
        ).fetchall()
        coverage = conn.execute("SELECT id, name, pack_id FROM coverage_items ORDER BY pack_id, name").fetchall()
    debt_rows = "".join(
        f"""
        <tr>
          <td>{esc(row['description'])}<br><span class="muted">{esc(row['evidence'])}</span></td>
          <td>{esc(row['pack_id'])}<br><span class="muted">{esc(row['coverage_name'] or '')}</span></td>
          <td>{esc(row['debt_type'])}</td>
          <td><span class="pill {'bad' if row['severity'] in {'critical','high'} else 'warn'}">{esc(row['severity'])}</span></td>
          <td>{status_pill(row['status'])}</td>
          <td>
            <form method="post" action="/knowledge-debt/{row['id']}/status">
              <div class="field"><label>Status</label><select name="status">{options(DEBT_STATUSES, row['status'])}</select></div>
              <button type="submit">Update</button>
            </form>
          </td>
        </tr>
        """
        for row in debts
    )
    coverage_options = '<option value="">No coverage link</option>' + "".join(
        f'<option value="{row["id"]}">{esc(row["pack_id"])} - {esc(row["name"])}</option>' for row in coverage
    )
    body = f"""
    <section class="split">
      <div class="card">
        <h2>Knowledge Debt</h2>
        <table><thead><tr><th>Debt</th><th>Scope</th><th>Type</th><th>Severity</th><th>Status</th><th>Update</th></tr></thead><tbody>{debt_rows}</tbody></table>
      </div>
      <div class="card">
        <h2>Add Knowledge Debt</h2>
        <form method="post" action="/knowledge-debt/create">
          <div class="field"><label>Pack ID</label><input name="pack_id" value="ogm.pack.north-american-outdoor" required></div>
          <div class="field"><label>Coverage Item</label><select name="coverage_item_id">{coverage_options}</select></div>
          <div class="field"><label>Debt Type</label><select name="debt_type">{options(DEBT_TYPES, 'low_coverage')}</select></div>
          <div class="field"><label>Severity</label><select name="severity">{options(['critical', 'high', 'medium', 'low'], 'medium')}</select></div>
          <div class="field"><label>Description</label><textarea name="description" required></textarea></div>
          <div class="field"><label>Evidence</label><textarea name="evidence"></textarea></div>
          <div class="field"><label>Recommended Action</label><textarea name="recommended_action"></textarea></div>
          <button type="submit">Add Debt</button>
        </form>
      </div>
    </section>
    """
    return layout("Knowledge Debt", body, "debt")


def logs_page(repo: Repository) -> bytes:
    with repo.connect() as conn:
        events = conn.execute(
            "SELECT e.*, m.mission_name FROM mission_events e LEFT JOIN missions m ON m.id = e.mission_id ORDER BY e.created_at DESC LIMIT 200"
        ).fetchall()
        logs = conn.execute(
            "SELECT l.*, m.mission_name FROM agent_logs l LEFT JOIN missions m ON m.id = l.mission_id ORDER BY l.created_at DESC LIMIT 200"
        ).fetchall()
        approvals = conn.execute("SELECT * FROM approvals ORDER BY created_at DESC LIMIT 200").fetchall()
    event_rows = "".join(
        f"<tr><td>{esc(row['created_at'])}</td><td>{esc(row['event_type'])}</td><td>{esc(row['mission_name'] or '')}</td><td>{esc(row['summary'])}</td><td>{esc(row['actor'])}</td></tr>"
        for row in events
    )
    log_rows = "".join(
        f"<tr><td>{esc(row['created_at'])}</td><td>{esc(row['log_level'])}</td><td>{esc(row['agent_name'])}</td><td>{esc(row['mission_name'] or '')}</td><td>{esc(row['message'])}</td></tr>"
        for row in logs
    )
    approval_rows = "".join(
        f"<tr><td>{esc(row['created_at'])}</td><td>{esc(row['target_type'])} #{esc(row['target_id'])}</td><td>{esc(row['decision'])}</td><td>{esc(row['approver'])}</td><td>{esc(row['reason'])}</td></tr>"
        for row in approvals
    )
    body = f"""
    <section class="card">
      <h2>Audit Trail</h2>
      <table><thead><tr><th>Time</th><th>Event</th><th>Mission</th><th>Summary</th><th>Actor</th></tr></thead><tbody>{event_rows}</tbody></table>
    </section>
    <section class="card" style="margin-top:16px;">
      <h2>Agent / CKO Logs</h2>
      <table><thead><tr><th>Time</th><th>Level</th><th>Actor</th><th>Mission</th><th>Message</th></tr></thead><tbody>{log_rows}</tbody></table>
    </section>
    <section class="card" style="margin-top:16px;">
      <h2>Approvals</h2>
      <table><thead><tr><th>Time</th><th>Target</th><th>Decision</th><th>Approver</th><th>Reason</th></tr></thead><tbody>{approval_rows}</tbody></table>
    </section>
    """
    return layout("Logs / Audit", body, "logs")


def settings_page(repo: Repository) -> bytes:
    stats = fetch_stats(repo)
    body = f"""
    <section class="card">
      <h2>Settings</h2>
      <p>This MVP is intentionally local and manual-first.</p>
      <table>
        <tr><th>Database</th><td>{esc(repo.db_path)}</td></tr>
        <tr><th>Specs Directory</th><td>{esc(ROOT / 'docs' / 'specs')}</td></tr>
        <tr><th>Autonomous Crawling</th><td><span class="pill bad">Disabled</span></td></tr>
        <tr><th>Autonomous Publishing</th><td><span class="pill bad">Disabled</span></td></tr>
        <tr><th>Expert Pack Compilation</th><td><span class="pill bad">Disabled</span></td></tr>
        <tr><th>Human Source Approval</th><td><span class="pill good">Required</span></td></tr>
        <tr><th>Human Mission Decisions</th><td><span class="pill good">Required</span></td></tr>
      </table>
    </section>
    <section class="card" style="margin-top:16px;">
      <h2>System Snapshot</h2>
      <pre>{esc(stats)}</pre>
    </section>
    """
    return layout("Settings", body, "settings")


def not_found_page() -> bytes:
    return layout("Not Found", '<section class="card"><h2>Not Found</h2><p>The requested page does not exist.</p></section>')


def parse_post(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length).decode("utf-8") if length else ""
    parsed = parse_qs(raw, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def redirect(handler: BaseHTTPRequestHandler, location: str) -> None:
    handler.send_response(HTTPStatus.SEE_OTHER)
    handler.send_header("Location", location)
    handler.end_headers()


class ControlCenterHandler(BaseHTTPRequestHandler):
    repo: Repository

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/":
            self.respond(dashboard_page(self.repo))
            return
        if path == "/missions":
            self.respond(missions_page(self.repo))
            return
        if path.startswith("/missions/"):
            mission_id = path.removeprefix("/missions/").strip("/")
            if mission_id.isdigit():
                self.respond(mission_detail_page(self.repo, int(mission_id)))
                return
        if path == "/source-review":
            self.respond(source_review_page(self.repo))
            return
        if path == "/coverage":
            self.respond(coverage_page(self.repo))
            return
        if path == "/knowledge-debt":
            self.respond(knowledge_debt_page(self.repo))
            return
        if path == "/logs":
            self.respond(logs_page(self.repo))
            return
        if path == "/settings":
            self.respond(settings_page(self.repo))
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.respond(not_found_page(), status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = unquote(urlparse(self.path).path)
        form = parse_post(self)
        if path == "/missions/create":
            self.create_mission(form)
            return
        if path.startswith("/missions/") and path.endswith("/status"):
            mission_id = path.split("/")[2]
            if mission_id.isdigit():
                self.update_mission_status(int(mission_id), form)
                return
        if path == "/sources/create":
            self.create_source(form)
            return
        if path.startswith("/sources/") and path.endswith("/review"):
            source_id = path.split("/")[2]
            if source_id.isdigit():
                self.review_source(int(source_id), form)
                return
        if path == "/coverage/create":
            self.create_coverage(form)
            return
        if path.startswith("/coverage/") and path.endswith("/update"):
            coverage_id = path.split("/")[2]
            if coverage_id.isdigit():
                self.update_coverage(int(coverage_id), form)
                return
        if path == "/knowledge-debt/create":
            self.create_debt(form)
            return
        if path.startswith("/knowledge-debt/") and path.endswith("/status"):
            debt_id = path.split("/")[2]
            if debt_id.isdigit():
                self.update_debt_status(int(debt_id), form)
                return
        if path == "/recommendations/create":
            self.create_recommendation(form)
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.respond(not_found_page(), status=HTTPStatus.NOT_FOUND)

    def respond(self, body: bytes, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def create_mission(self, form: dict[str, str]) -> None:
        now = utc_now()
        fields = {
            "mission_name": form.get("mission_name", "").strip(),
            "target_expert_pack": form.get("target_expert_pack", "").strip(),
            "priority": form.get("priority", "medium"),
            "status": form.get("status", "created"),
            "human_reviewer": form.get("human_reviewer", "").strip(),
            "required_deliverables": form.get("required_deliverables", "").strip(),
            "coverage_goal": form.get("coverage_goal", "").strip(),
            "completion_criteria": form.get("completion_criteria", "").strip(),
            "allowed_source_types": form.get("allowed_source_types", "").strip(),
            "approved_domains": form.get("approved_domains", "").strip(),
        }
        with self.repo.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO missions (
                    mission_name, target_expert_pack, priority, status, human_reviewer,
                    required_deliverables, coverage_goal, completion_criteria,
                    allowed_source_types, approved_domains, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fields["mission_name"],
                    fields["target_expert_pack"],
                    fields["priority"],
                    fields["status"],
                    fields["human_reviewer"],
                    fields["required_deliverables"],
                    fields["coverage_goal"],
                    fields["completion_criteria"],
                    fields["allowed_source_types"],
                    fields["approved_domains"],
                    now,
                    now,
                ),
            )
            mission_id = cur.lastrowid
            self.repo.audit(
                conn,
                mission_id=mission_id,
                event_type="mission_created",
                summary=f"Mission created with status {fields['status']}.",
                after_state=fields["status"],
            )
            self.repo.log(conn, mission_id=mission_id, agent_name="CKO", message="Mission is ready for human governance and manual source work.")
        redirect(self, f"/missions/{mission_id}")

    def update_mission_status(self, mission_id: int, form: dict[str, str]) -> None:
        new_status = form.get("status", "created")
        reason = form.get("reason", "Human decision recorded.").strip()
        now = utc_now()
        with self.repo.connect() as conn:
            mission = conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
            if mission is None:
                redirect(self, "/missions")
                return
            before = mission["status"]
            conn.execute(
                "UPDATE missions SET status = ?, updated_at = ? WHERE id = ?",
                (new_status, now, mission_id),
            )
            conn.execute(
                """
                INSERT INTO approvals (target_type, target_id, decision, approver, reason, created_at)
                VALUES ('mission_status', ?, ?, 'human', ?, ?)
                """,
                (mission_id, new_status, reason, now),
            )
            self.repo.audit(
                conn,
                mission_id=mission_id,
                event_type="mission_status_updated",
                summary=reason,
                before_state=before,
                after_state=new_status,
            )
            self.repo.log(conn, mission_id=mission_id, agent_name="CKO", message=f"Mission status changed from {before} to {new_status}.")
        redirect(self, f"/missions/{mission_id}")

    def create_source(self, form: dict[str, str]) -> None:
        now = utc_now()
        mission_id = int(form.get("mission_id", "0") or "0")
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT INTO source_candidates (
                    mission_id, title, url_or_path, source_type, source_class,
                    quality_score, quality_confidence, relevance_score, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mission_id,
                    form.get("title", "").strip(),
                    form.get("url_or_path", "").strip(),
                    form.get("source_type", "").strip(),
                    form.get("source_class", "Unknown Source"),
                    to_float(form.get("quality_score", "0")),
                    to_float(form.get("quality_confidence", "0.5")),
                    to_float(form.get("relevance_score", "0")),
                    form.get("notes", "").strip(),
                    now,
                    now,
                ),
            )
            source_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            self.repo.audit(
                conn,
                mission_id=mission_id,
                event_type="source_candidate_added",
                summary=f"Manual source candidate #{source_id} added.",
                after_state="candidate_found",
            )
            self.repo.log(conn, mission_id=mission_id, agent_name="CKO", message="Manual source candidate added. Human approval is required before intake.")
        redirect(self, f"/missions/{mission_id}" if mission_id else "/source-review")

    def review_source(self, source_id: int, form: dict[str, str]) -> None:
        decision = form.get("decision", "needs_license_review")
        reason = form.get("reason", "").strip()
        now = utc_now()
        with self.repo.connect() as conn:
            source = conn.execute("SELECT * FROM source_candidates WHERE id = ?", (source_id,)).fetchone()
            if source is None:
                redirect(self, "/source-review")
                return
            before = source["status"]
            conn.execute(
                "UPDATE source_candidates SET status = ?, license_state = ?, updated_at = ? WHERE id = ?",
                (decision, "approved" if decision.startswith("approved") else decision, now, source_id),
            )
            conn.execute(
                """
                INSERT INTO source_reviews (source_id, decision, reviewer, reason, created_at)
                VALUES (?, ?, 'human', ?, ?)
                """,
                (source_id, decision, reason, now),
            )
            conn.execute(
                """
                INSERT INTO approvals (target_type, target_id, decision, approver, reason, created_at)
                VALUES ('source', ?, ?, 'human', ?, ?)
                """,
                (source_id, decision, reason, now),
            )
            self.repo.audit(
                conn,
                mission_id=source["mission_id"],
                event_type="source_reviewed",
                summary=f"Source #{source_id} reviewed: {decision}. {reason}",
                before_state=before,
                after_state=decision,
            )
            self.repo.log(conn, mission_id=source["mission_id"], agent_name="CKO", message=f"Source #{source_id} received human decision: {decision}.")
        redirect(self, "/source-review")

    def create_coverage(self, form: dict[str, str]) -> None:
        now = utc_now()
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT INTO coverage_items (
                    pack_id, name, domain_path, target_percent, current_percent,
                    measurement_method, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    form.get("pack_id", "").strip(),
                    form.get("name", "").strip(),
                    form.get("domain_path", "").strip(),
                    to_float(form.get("target_percent", "100"), 100.0),
                    to_float(form.get("current_percent", "0")),
                    form.get("measurement_method", "").strip(),
                    form.get("notes", "").strip(),
                    now,
                ),
            )
            self.repo.audit(conn, mission_id=None, event_type="coverage_item_created", summary=f"Coverage item created: {form.get('name', '').strip()}.")
        redirect(self, "/coverage")

    def update_coverage(self, coverage_id: int, form: dict[str, str]) -> None:
        now = utc_now()
        with self.repo.connect() as conn:
            conn.execute(
                "UPDATE coverage_items SET current_percent = ?, notes = ?, updated_at = ? WHERE id = ?",
                (to_float(form.get("current_percent", "0")), form.get("notes", "").strip(), now, coverage_id),
            )
            self.repo.audit(conn, mission_id=None, event_type="coverage_updated", summary=f"Coverage item #{coverage_id} updated.")
        redirect(self, "/coverage")

    def create_debt(self, form: dict[str, str]) -> None:
        now = utc_now()
        coverage_item = form.get("coverage_item_id") or None
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_debt (
                    pack_id, coverage_item_id, debt_type, severity, description,
                    evidence, recommended_action, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    form.get("pack_id", "").strip(),
                    int(coverage_item) if coverage_item else None,
                    form.get("debt_type", "low_coverage"),
                    form.get("severity", "medium"),
                    form.get("description", "").strip(),
                    form.get("evidence", "").strip(),
                    form.get("recommended_action", "").strip(),
                    now,
                    now,
                ),
            )
            self.repo.audit(conn, mission_id=None, event_type="knowledge_debt_created", summary=f"Knowledge Debt created: {form.get('description', '').strip()[:120]}.")
        redirect(self, "/knowledge-debt")

    def update_debt_status(self, debt_id: int, form: dict[str, str]) -> None:
        now = utc_now()
        status = form.get("status", "open")
        with self.repo.connect() as conn:
            conn.execute(
                "UPDATE knowledge_debt SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, debt_id),
            )
            self.repo.audit(conn, mission_id=None, event_type="knowledge_debt_status_updated", summary=f"Knowledge Debt #{debt_id} status changed to {status}.")
        redirect(self, "/knowledge-debt")

    def create_recommendation(self, form: dict[str, str]) -> None:
        now = utc_now()
        mission_id_raw = form.get("mission_id") or None
        mission_id = int(mission_id_raw) if mission_id_raw else None
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT INTO cko_recommendations (
                    mission_id, recommendation_type, title, body, priority, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mission_id,
                    form.get("recommendation_type", "future_work").strip() or "future_work",
                    form.get("title", "").strip(),
                    form.get("body", "").strip(),
                    form.get("priority", "medium"),
                    now,
                    now,
                ),
            )
            self.repo.audit(conn, mission_id=mission_id, event_type="cko_recommendation_added", summary=f"Manual CKO recommendation added: {form.get('title', '').strip()}.", actor="human")
            self.repo.log(conn, mission_id=mission_id, agent_name="CKO", message=f"Manual recommendation added: {form.get('title', '').strip()}.")
        redirect(self, f"/missions/{mission_id}" if mission_id else "/")

    def log_message(self, format: str, *args: Any) -> None:
        # Keep terminal logs readable while avoiding noisy per-asset output.
        print(f"{self.address_string()} - {format % args}")


def run(host: str, port: int, db_path: Path) -> None:
    init_db(db_path)
    repo = Repository(db_path)

    class Handler(ControlCenterHandler):
        pass

    Handler.repo = repo
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"{APP_NAME} running at http://{host}:{port}")
    print(f"SQLite database: {db_path}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("OGM_CONTROL_CENTER_PORT", "8765")))
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("OGM_CONTROL_CENTER_DB", DEFAULT_DB_PATH)))
    args = parser.parse_args()
    run(args.host, args.port, args.db)


if __name__ == "__main__":
    main()
