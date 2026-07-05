"""Manages the three tiers of "memory" the app cares about:

1. Ephemeral turn context — the in-flight utterance, streaming token
   buffer, and recording buffer. Lives only in local variables inside
   `engine/interface.py` and is never written anywhere.
2. Current session context — this conversation's message history.
   Persisted turn-by-turn to SQLite via `Repository`, and replayed (the
   most recent `history_turns_in_prompt` turns) into every prompt.
3. Long-term memory — `memory_facts` rows, which persist across session
   resets and are injected into every prompt regardless of how much chat
   history has been cleared.

This module owns (2) and knows how to summarize what falls outside the
verbatim replay window. It deliberately does not do anything LLM-based —
the summary is a cheap, deterministic, rule-based line, matching the same
"keep it simple" approach used for the headset's session summarizer in
docs/09-insight-v1-spec.md.
"""

from __future__ import annotations

from storage.models import Message, Session
from storage.repository import Repository


class SessionManager:
    def __init__(self, repo: Repository, history_turns_in_prompt: int = 6):
        self._repo = repo
        self._history_turns_in_prompt = history_turns_in_prompt
        self.current_session: Session = self._resume_or_create()

    def _resume_or_create(self) -> Session:
        existing = self._repo.get_latest_active_session()
        return existing if existing is not None else self._repo.create_session()

    # ------------------------------------------------------------------

    def record_user_message(self, text: str, source: str = "text") -> Message:
        return self._repo.add_message(self.current_session.id, role="user", content=text, source=source)

    def record_assistant_message(
        self,
        text: str,
        prompt_version_id: str | None,
        latency_ms: int,
        cancelled: bool = False,
    ) -> Message:
        return self._repo.add_message(
            self.current_session.id,
            role="assistant",
            content=text,
            source="text",
            prompt_version_id=prompt_version_id,
            latency_ms=latency_ms,
            cancelled=cancelled,
        )

    def get_all_messages(self) -> list[Message]:
        return self._repo.get_session_messages(self.current_session.id)

    def message_count(self) -> int:
        return self._repo.count_session_messages(self.current_session.id)

    def get_prompt_history_messages(self) -> tuple[list[dict], str | None]:
        """Returns (chat_messages_for_prompt, summary_note_or_none).

        Only the most recent `history_turns_in_prompt` *turns* (a turn =
        one user + one assistant message) are replayed verbatim. Anything
        older is represented only as a one-line summary note, keeping the
        context window bounded regardless of how long the conversation
        runs."""
        messages = self.get_all_messages()
        max_messages = self._history_turns_in_prompt * 2
        recent = messages[-max_messages:] if max_messages > 0 else messages
        older_count = max(0, len(messages) - len(recent))

        chat_messages = [{"role": m.role, "content": m.content} for m in recent if m.role in ("user", "assistant")]

        summary_note = None
        if older_count > 0:
            summary_note = f"({older_count} earlier message(s) in this session are not shown verbatim.)"

        return chat_messages, summary_note

    def reset(self, clear_memory_facts: bool = False) -> Session:
        """Ends the current session and starts a fresh one. The old
        session's rows stay in SQLite (nothing is deleted) — this just
        gives the conversation a clean slate going forward. If
        `clear_memory_facts` is True, long-term memory facts are cleared
        too (a "full reset," not just a new chat)."""
        self._repo.end_session(self.current_session.id)
        if clear_memory_facts:
            self._repo.clear_all_memory_facts()
        self.current_session = self._repo.create_session()
        return self.current_session
