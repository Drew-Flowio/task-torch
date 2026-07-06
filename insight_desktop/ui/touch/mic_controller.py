"""Microphone interaction controller for the Pi touch UI."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QTimer, Signal

from engine.interface import InsightEngine
from engine.types import AppState, TurnResult
from ui.touch.interaction_state import STATE_COLORS, STATE_LABELS, TouchInteractionState
from ui.workers import ConversationUtteranceWorker, VoiceUtteranceWorker

logger = logging.getLogger("insight.ui.touch.mic")


class MicController(QObject):
    """Orchestrates one-shot and conversation microphone modes."""

    state_changed = Signal(object)  # TouchInteractionState
    status_message = Signal(str)
    answer_ready = Signal(object)  # TurnResult | None
    error_occurred = Signal(str)
    transcript_ready = Signal(str)

    def __init__(self, engine: InsightEngine, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._state = TouchInteractionState.READY
        self._conversation_active = False
        self._worker = None
        self._busy = False

        self._vad_poll = QTimer(self)
        self._vad_poll.setInterval(150)
        self._vad_poll.timeout.connect(self._poll_vad)

    @property
    def state(self) -> TouchInteractionState:
        return self._state

    @property
    def conversation_active(self) -> bool:
        return self._conversation_active

    def is_busy(self) -> bool:
        return self._busy or self._worker is not None

    def can_start_interaction(self) -> bool:
        return self._state in (
            TouchInteractionState.READY,
            TouchInteractionState.ERROR,
        ) and not self.is_busy()

    # ------------------------------------------------------------------
    # One-shot
    # ------------------------------------------------------------------

    def start_one_shot_recording(self) -> None:
        if not self.can_start_interaction() or self._conversation_active:
            return
        self._engine.start_recording()
        self._set_state(TouchInteractionState.ONE_SHOT_RECORDING)

    def stop_one_shot_recording(self) -> None:
        if self._state != TouchInteractionState.ONE_SHOT_RECORDING or self._busy:
            return
        self._busy = True
        worker = VoiceUtteranceWorker(self._engine)
        worker.state_changed.connect(lambda s: self.on_engine_state(AppState(s)))
        worker.transcript_ready.connect(self.transcript_ready.emit)
        worker.finished_ok.connect(self._on_one_shot_finished)
        worker.failed.connect(self._on_worker_failed)
        worker.finished.connect(self._clear_worker)
        self._worker = worker
        worker.start()

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------

    def enter_conversation_mode(self) -> None:
        if not self.can_start_interaction():
            return
        self._conversation_active = True
        self.status_message.emit("Talk naturally. I'll listen after each answer.")
        self.start_conversation_listening()

    def exit_conversation_mode(self) -> None:
        self._conversation_active = False
        self._vad_poll.stop()
        if self._engine.is_recording():
            self._engine.cancel_recording()
        self._engine.cancel_current()
        self._busy = False
        self._worker = None
        self._set_state(TouchInteractionState.READY)

    def start_conversation_listening(self) -> None:
        if not self._conversation_active or self._busy:
            return
        if self._engine.is_recording():
            return
        self._engine.start_vad_listening()
        self._set_state(TouchInteractionState.CONVERSATION_LISTENING)
        self._vad_poll.start()

    def handle_conversation_utterance(self) -> None:
        if not self._conversation_active or self._busy:
            return
        self._vad_poll.stop()
        self._busy = True
        worker = ConversationUtteranceWorker(self._engine)
        worker.state_changed.connect(lambda s: self.on_engine_state(AppState(s)))
        worker.transcript_ready.connect(self.transcript_ready.emit)
        worker.finished_ok.connect(self._on_conversation_turn_finished)
        worker.failed.connect(self._on_conversation_failed)
        worker.finished.connect(self._clear_worker)
        self._worker = worker
        worker.start()

    def resume_conversation_after_speaking(self) -> None:
        if not self._conversation_active:
            self._set_state(TouchInteractionState.READY)
            return
        self._busy = False
        self.start_conversation_listening()

    def _poll_vad(self) -> None:
        if not self._conversation_active or self._busy:
            return
        if self._engine.vad_listen_finished():
            self.handle_conversation_utterance()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_one_shot_finished(self, result: TurnResult | None) -> None:
        self._busy = False
        if result is None:
            self._set_state(TouchInteractionState.READY)
            return
        self.answer_ready.emit(result)
        self._set_state(TouchInteractionState.READY)

    def _on_conversation_turn_finished(self, result: TurnResult | None) -> None:
        self._busy = False
        if result is None:
            self._set_state(TouchInteractionState.CONVERSATION_WAITING)
            self.status_message.emit("Listening…")
            QTimer.singleShot(300, self.start_conversation_listening)
            return
        self.answer_ready.emit(result)
        self.resume_conversation_after_speaking()

    def _on_conversation_failed(self, message: str) -> None:
        self._busy = False
        logger.warning("Conversation turn failed: %s", message)
        self.error_occurred.emit(message[:80])
        if self._conversation_active:
            self._set_state(TouchInteractionState.CONVERSATION_WAITING)
            QTimer.singleShot(600, self.start_conversation_listening)
        else:
            self._set_state(TouchInteractionState.READY)

    def _on_worker_failed(self, message: str) -> None:
        self._busy = False
        self.error_occurred.emit(message)
        self._set_state(TouchInteractionState.ERROR)

    def _clear_worker(self) -> None:
        self._worker = None

    def _set_state(self, state: TouchInteractionState) -> None:
        self._state = state
        self.state_changed.emit(state)

    @staticmethod
    def label_for(state: TouchInteractionState) -> str:
        return STATE_LABELS.get(state, state.value)

    @staticmethod
    def color_for(state: TouchInteractionState) -> str:
        return STATE_COLORS.get(state, "#6b6b75")

    def map_engine_state(self, engine_state: AppState) -> TouchInteractionState | None:
        mapping = {
            AppState.TRANSCRIBING: TouchInteractionState.TRANSCRIBING,
            AppState.THINKING: TouchInteractionState.THINKING,
            AppState.SPEAKING: TouchInteractionState.SPEAKING,
        }
        if self._state == TouchInteractionState.ONE_SHOT_RECORDING:
            return mapping.get(engine_state)
        if self._conversation_active:
            return mapping.get(engine_state)
        return None

    def on_engine_state(self, engine_state: AppState) -> None:
        mapped = self.map_engine_state(engine_state)
        if mapped is not None:
            self._set_state(mapped)
