"""QThread workers that call InsightEngine off the UI thread.

This is the *only* place in the app that touches Qt threading. The
engine itself knows nothing about Qt - these workers just wrap a blocking
engine call and translate its plain-Python callbacks (`on_token`,
`on_state`, `on_transcript`) into Qt signals, which are safe to cross
from a worker thread into the main/UI thread.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from engine.interface import InsightEngine
from engine.types import AppState


class BaseEngineWorker(QThread):
    token_received = Signal(str)
    state_changed = Signal(str)  # AppState value, as plain text for a simple cross-thread signal
    finished_ok = Signal(object)  # TurnResult | None
    failed = Signal(str)

    def _emit_token(self, piece: str) -> None:
        self.token_received.emit(piece)

    def _emit_state(self, state: AppState) -> None:
        self.state_changed.emit(state.value)


class TextMessageWorker(BaseEngineWorker):
    """Runs `InsightEngine.send_text_message()` on a background thread."""

    def __init__(self, engine: InsightEngine, text: str):
        super().__init__()
        self._engine = engine
        self._text = text

    def run(self) -> None:
        try:
            result = self._engine.send_text_message(
                self._text, on_token=self._emit_token, on_state=self._emit_state,
            )
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001 - surface any adapter failure to the UI
            self.failed.emit(str(exc))


class PhotoGreetingWorker(BaseEngineWorker):
    def __init__(self, engine: InsightEngine):
        super().__init__()
        self._engine = engine

    def run(self) -> None:
        try:
            result = self._engine.greet_after_photo(
                on_token=self._emit_token, on_state=self._emit_state,
            )
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class PhotoAttachWorker(BaseEngineWorker):
    """Runs `InsightEngine.attach_photo()` on a background thread."""

    photo_ready = Signal(str, str)  # image_path, caption

    def __init__(self, engine: InsightEngine, image_path: str):
        super().__init__()
        self._engine = engine
        self._image_path = image_path

    def run(self) -> None:
        try:
            ctx = self._engine.attach_photo(
                self._image_path, on_state=lambda s: self._emit_state(s),
            )
            self.photo_ready.emit(ctx.image_path, ctx.caption)
            self.finished_ok.emit(None)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ConversationUtteranceWorker(BaseEngineWorker):
    """Processes a completed VAD utterance in conversation mode."""

    transcript_ready = Signal(str)

    def run(self) -> None:
        try:
            result = self._engine.process_vad_utterance(
                on_transcript=self.transcript_ready.emit,
                on_token=self._emit_token,
                on_state=self._emit_state,
            )
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class VoiceTextSendWorker(BaseEngineWorker):
    """Send finalized transcript as text, then speak the reply (UI orchestration)."""

    def __init__(self, engine: InsightEngine, text: str):
        super().__init__()
        self._engine = engine
        self._text = text

    def run(self) -> None:
        try:
            result = self._engine.send_text_message(
                self._text, on_token=self._emit_token, on_state=self._emit_state,
            )
            if result.reply_text and not result.cancelled:
                self._emit_state(AppState.SPEAKING)
                self._engine.speak(result.reply_text)
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class VoiceUtteranceWorker(BaseEngineWorker):
    """Runs `InsightEngine.send_voice_utterance()` on a background thread
    (transcription -> LLM -> TTS playback, all off the UI thread)."""

    transcript_ready = Signal(str)

    def __init__(self, engine: InsightEngine):
        super().__init__()
        self._engine = engine

    def run(self) -> None:
        try:
            result = self._engine.send_voice_utterance(
                on_transcript=self.transcript_ready.emit,
                on_token=self._emit_token,
                on_state=self._emit_state,
            )
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
