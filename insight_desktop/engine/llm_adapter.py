"""Adapts a local GGUF instruction model (via llama-cpp-python) into the
engine's LLM interface.

CURRENT MODEL (set in config/config.yaml -> models.llm_model_path)
--------------------------------------------------------------
By default this points at the same model already validated elsewhere in
this repo: Phi-3.5-mini-instruct (Microsoft, MIT license) —
see docs/01-model-choice.md and docs/08-model-swap-mit.md.

This file has zero model-specific logic. It only ever sees a GGUF path
and a chat message list; llama-cpp-python reads the chat template baked
into the GGUF's own metadata. Swapping models is a one-line change to
`models.llm_model_path` in config/config.yaml — nothing here changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from llama_cpp import Llama


@dataclass(frozen=True)
class LlmConfig:
    model_path: str
    n_ctx: int = 4096
    n_threads: int = 8
    max_tokens: int = 200
    temperature: float = 0.4
    top_p: float = 0.9


class LlmAdapterProtocol(Protocol):
    """Interface both the real and mock LLM adapters satisfy, so
    `engine/interface.py` never needs to know which one it's holding."""

    def generate(
        self,
        messages: list[dict],
        on_token: Callable[[str], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> str: ...


class LlmAdapter:
    """Thin, swappable wrapper around a local chat-completion-capable
    GGUF model, loaded once and reused for every turn."""

    def __init__(self, config: LlmConfig):
        self._config = config
        self._llm = Llama(
            model_path=config.model_path,
            n_ctx=config.n_ctx,
            n_threads=config.n_threads,
            verbose=False,
        )

    def generate(
        self,
        messages: list[dict],
        on_token: Callable[[str], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> str:
        """Runs a streaming chat completion. `on_token` is called with
        each new text chunk as it's generated (for live UI updates). If
        `should_cancel()` returns True mid-stream, generation stops
        immediately and the partial text collected so far is returned —
        this is what backs the app's Stop/Cancel button."""
        stream = self._llm.create_chat_completion(
            messages=messages,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
            top_p=self._config.top_p,
            stream=True,
        )

        pieces: list[str] = []
        for chunk in stream:
            if should_cancel is not None and should_cancel():
                break
            delta = chunk["choices"][0].get("delta", {})
            piece = delta.get("content")
            if piece:
                pieces.append(piece)
                if on_token is not None:
                    on_token(piece)

        return "".join(pieces).strip()
