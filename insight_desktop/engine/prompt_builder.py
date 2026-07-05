"""Assembles the exact message list sent to the LLM for a single turn."""

from __future__ import annotations

from engine.visual_context import VisualContext


class PromptBuilder:
    def build(
        self,
        personality_prompt: str,
        memory_facts: list[str],
        history_messages: list[dict],
        history_summary_note: str | None,
        current_utterance: str,
        visual_context: VisualContext | None = None,
    ) -> tuple[list[dict], str]:
        system_content = personality_prompt.strip()

        if memory_facts:
            facts_block = "\n".join(f"- {fact}" for fact in memory_facts)
            system_content += f"\n\nThings you know about the user (long-term memory):\n{facts_block}"

        if visual_context is not None:
            system_content += f"\n\n{visual_context.prompt_block()}"

        if history_summary_note:
            system_content += f"\n\n{history_summary_note}"

        messages: list[dict] = [{"role": "system", "content": system_content}]
        messages.extend(history_messages)
        messages.append({"role": "user", "content": current_utterance})

        debug_text = "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in messages)
        return messages, debug_text
