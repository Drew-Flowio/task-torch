"""Mock LLM / STT / TTS adapters, used when `engine.mock_mode: true` in
config/config.yaml.

These satisfy the exact same protocols as the real adapters
(`LlmAdapterProtocol`, `SttAdapterProtocol`, `TtsAdapterProtocol`), so
`engine/interface.py` never has an `if mock:` branch anywhere except the
one place that constructs the adapters. Useful for:

- Developing or demoing the UI on a machine without the multi-GB models
  downloaded.
- Fast, deterministic smoke-testing of the app's plumbing (chat history,
  prompt versioning, memory facts, cancel/stop behavior) without waiting
  on real inference.
"""

from __future__ import annotations

import time
from typing import Callable

_CANNED_REPLIES = [
    "Alright, from what I'm seeing — start with the obvious check first, then we'll go from there.",
    "Yeah, that's a fair question. What's the goal here — fix it, or just figure out if it's safe?",
    "Okay cool, I'd poke at the simple stuff before tearing anything apart.",
]


class MockVisionAdapter:
    def describe_image(self, image_path: str) -> str:  # noqa: ARG002
        time.sleep(0.5)
        return (
            "A stainless steel electric kettle on a kitchen counter. "
            "The power cord is plugged in and there's no visible damage."
        )


class MockLlmAdapter:
    def __init__(self) -> None:
        self._call_count = 0

    def generate(
        self,
        messages: list[dict],
        on_token: Callable[[str], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> str:
        reply = _CANNED_REPLIES[self._call_count % len(_CANNED_REPLIES)]
        self._call_count += 1

        words = reply.split(" ")
        pieces: list[str] = []
        for i, word in enumerate(words):
            if should_cancel is not None and should_cancel():
                break
            piece = word + (" " if i < len(words) - 1 else "")
            pieces.append(piece)
            if on_token is not None:
                on_token(piece)
            time.sleep(0.03)  # simulate token-by-token streaming latency
        return "".join(pieces).strip()


class MockSttAdapter:
    def transcribe(self, audio_path: str) -> str:  # noqa: ARG002
        time.sleep(0.3)
        return "This is a mock transcription of what I just said."


class MockTtsAdapter:
    def __init__(self) -> None:
        self._speaking = False

    def speak(self, text: str) -> None:
        self._speaking = True
        # Simulate roughly real-time playback without touching real audio
        # hardware, so mock mode also works in headless/CI environments.
        duration = min(4.0, max(0.4, len(text) / 40))
        elapsed = 0.0
        while elapsed < duration and self._speaking:
            time.sleep(0.05)
            elapsed += 0.05
        self._speaking = False

    def stop(self) -> None:
        self._speaking = False
