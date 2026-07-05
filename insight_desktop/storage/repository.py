"""The one place that runs SQL. Everything else in the app (engine, UI)
reads and writes conversation history, prompt versions, and memory facts
only through this Repository — never through raw sqlite3 calls of their
own.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from storage import db
from storage.models import MemoryFact, Message, PromptVersion, Session


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


class Repository:
    def __init__(self, db_path: str):
        self._conn: sqlite3.Connection = db.connect(db_path)

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self) -> Session:
        session = Session(id=_new_id(), started_at=_now(), ended_at=None, status="active")
        self._conn.execute(
            "INSERT INTO sessions (id, started_at, ended_at, status) VALUES (?, ?, ?, ?)",
            (session.id, session.started_at, session.ended_at, session.status),
        )
        self._conn.commit()
        return session

    def end_session(self, session_id: str) -> None:
        self._conn.execute(
            "UPDATE sessions SET status = 'ended', ended_at = ? WHERE id = ?",
            (_now(), session_id),
        )
        self._conn.commit()

    def get_latest_active_session(self) -> Session | None:
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE status = 'active' ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return _row_to_session(row) if row else None

    def list_sessions(self, limit: int = 50) -> list[Session]:
        rows = self._conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_session(r) for r in rows]

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        source: str = "text",
        prompt_version_id: str | None = None,
        latency_ms: int | None = None,
        cancelled: bool = False,
    ) -> Message:
        message = Message(
            id=_new_id(),
            session_id=session_id,
            ts=_now(),
            role=role,
            content=content,
            source=source,
            prompt_version_id=prompt_version_id,
            latency_ms=latency_ms,
            cancelled=cancelled,
        )
        self._conn.execute(
            """INSERT INTO messages
               (id, session_id, ts, role, content, source, prompt_version_id, latency_ms, cancelled)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message.id, message.session_id, message.ts, message.role, message.content,
                message.source, message.prompt_version_id, message.latency_ms, int(message.cancelled),
            ),
        )
        self._conn.commit()
        return message

    def get_session_messages(self, session_id: str, limit: int = 500) -> list[Message]:
        rows = self._conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY ts ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    def count_session_messages(self, session_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE session_id = ?", (session_id,)
        ).fetchone()
        return int(row["c"])

    # ------------------------------------------------------------------
    # Prompt versions
    # ------------------------------------------------------------------

    def save_prompt_version(self, content: str, label: str | None = None) -> PromptVersion:
        version = PromptVersion(id=_new_id(), content=content, label=label, created_at=_now(), is_active=True)
        self._conn.execute("UPDATE prompt_versions SET is_active = 0")
        self._conn.execute(
            "INSERT INTO prompt_versions (id, content, label, created_at, is_active) VALUES (?, ?, ?, ?, 1)",
            (version.id, version.content, version.label, version.created_at),
        )
        self._conn.commit()
        return version

    def get_active_prompt_version(self) -> PromptVersion | None:
        row = self._conn.execute(
            "SELECT * FROM prompt_versions WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return _row_to_prompt_version(row) if row else None

    def activate_prompt_version(self, version_id: str) -> PromptVersion | None:
        self._conn.execute("UPDATE prompt_versions SET is_active = 0")
        self._conn.execute("UPDATE prompt_versions SET is_active = 1 WHERE id = ?", (version_id,))
        self._conn.commit()
        row = self._conn.execute("SELECT * FROM prompt_versions WHERE id = ?", (version_id,)).fetchone()
        return _row_to_prompt_version(row) if row else None

    def list_prompt_versions(self, limit: int = 50) -> list[PromptVersion]:
        rows = self._conn.execute(
            "SELECT * FROM prompt_versions ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_prompt_version(r) for r in rows]

    # ------------------------------------------------------------------
    # Memory facts
    # ------------------------------------------------------------------

    def add_memory_fact(self, text: str) -> MemoryFact:
        fact = MemoryFact(id=_new_id(), text=text, created_at=_now(), active=True)
        self._conn.execute(
            "INSERT INTO memory_facts (id, text, created_at, active) VALUES (?, ?, ?, 1)",
            (fact.id, fact.text, fact.created_at),
        )
        self._conn.commit()
        return fact

    def list_memory_facts(self, active_only: bool = True) -> list[MemoryFact]:
        if active_only:
            rows = self._conn.execute(
                "SELECT * FROM memory_facts WHERE active = 1 ORDER BY created_at ASC"
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM memory_facts ORDER BY created_at ASC").fetchall()
        return [_row_to_memory_fact(r) for r in rows]

    def remove_memory_fact(self, fact_id: str) -> None:
        self._conn.execute("UPDATE memory_facts SET active = 0 WHERE id = ?", (fact_id,))
        self._conn.commit()

    def clear_all_memory_facts(self) -> None:
        self._conn.execute("UPDATE memory_facts SET active = 0")
        self._conn.commit()


# ----------------------------------------------------------------------
# Row -> dataclass helpers
# ----------------------------------------------------------------------

def _row_to_session(row: sqlite3.Row) -> Session:
    return Session(id=row["id"], started_at=row["started_at"], ended_at=row["ended_at"], status=row["status"])


def _row_to_message(row: sqlite3.Row) -> Message:
    return Message(
        id=row["id"],
        session_id=row["session_id"],
        ts=row["ts"],
        role=row["role"],
        content=row["content"],
        source=row["source"],
        prompt_version_id=row["prompt_version_id"],
        latency_ms=row["latency_ms"],
        cancelled=bool(row["cancelled"]),
    )


def _row_to_prompt_version(row: sqlite3.Row) -> PromptVersion:
    return PromptVersion(
        id=row["id"], content=row["content"], label=row["label"],
        created_at=row["created_at"], is_active=bool(row["is_active"]),
    )


def _row_to_memory_fact(row: sqlite3.Row) -> MemoryFact:
    return MemoryFact(id=row["id"], text=row["text"], created_at=row["created_at"], active=bool(row["active"]))
