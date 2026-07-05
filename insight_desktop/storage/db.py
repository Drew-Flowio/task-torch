"""SQLite connection + schema management for the Insight desktop app.

Everything Insight persists lives in one local SQLite file (path set by
``storage.db_path`` in config/config.yaml). This module owns the schema
and connection; `storage/repository.py` is the only other module allowed
to run queries against it.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    started_at  TEXT NOT NULL,
    ended_at    TEXT,
    status      TEXT NOT NULL DEFAULT 'active'   -- active | ended
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id          TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    label       TEXT,
    created_at  TEXT NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id                  TEXT PRIMARY KEY,
    session_id          TEXT NOT NULL REFERENCES sessions(id),
    ts                  TEXT NOT NULL,
    role                TEXT NOT NULL,             -- user | assistant | system
    content             TEXT NOT NULL,
    source              TEXT NOT NULL DEFAULT 'text',  -- text | voice
    prompt_version_id   TEXT REFERENCES prompt_versions(id),
    latency_ms          INTEGER,
    cancelled           INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS memory_facts (
    id          TEXT PRIMARY KEY,
    text        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    active      INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, ts);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_active ON prompt_versions(is_active);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Opens (creating if needed) the SQLite database and ensures the
    schema exists. One connection is created per process and shared via
    the Repository — SQLite handles the light concurrency this app needs
    (one UI, one background worker thread at a time) without a pool."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
