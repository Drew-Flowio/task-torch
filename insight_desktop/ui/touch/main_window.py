"""Touch-first main screen for Raspberry Pi / Offgrid Minds."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from engine.interface import InsightEngine
from engine.types import AppState, TurnResult
from ui.touch import tokens as t
from ui.touch.app_mode import AppMode
from ui.touch.components.chat_screen import TouchChatView
from ui.touch.components.expert_pack_sheet import ExpertPackSheet
from ui.touch.components.expert_pack_strip import ExpertPackStrip
from ui.touch.components.header_bar import InstrumentHeader
from ui.touch.components.mode_switcher import ModeSwitcher
from ui.touch.components.scan_screen import ScanScreen
from ui.touch.components.talk_screen import TalkScreen
from ui.touch.expert_packs import ExpertPackStore
from ui.touch.interaction_state import STATE_LABELS, TouchInteractionState
from ui.touch.live_transcript import LiveTranscriptTap, PartialTranscribeWorker, SttPaths
from ui.touch.mic_controller import MicController
from ui.touch.settings_sheet import SettingsSheet
from ui.workers import (
    BaseEngineWorker,
    PhotoAttachWorker,
    PhotoGreetingWorker,
    TextMessageWorker,
    VoiceTextSendWorker,
)

logger = logging.getLogger("insight.ui.touch")


class TouchMainWindow(QMainWindow):
    """Three-mode field instrument: Scan · Talk · Chat."""

    def __init__(
        self,
        engine: InsightEngine,
        assistant_name: str = "Offgrid Minds",
        screen_inches: int = 7,
        stt_paths: SttPaths | None = None,
        input_device: int | str | None = None,
    ) -> None:
        super().__init__()
        self._engine = engine
        self._assistant_name = assistant_name
        self._screen_inches = screen_inches
        self._worker: BaseEngineWorker | None = None
        self._finalize_worker: PartialTranscribeWorker | None = None
        self._touch_state = TouchInteractionState.READY
        self._app_mode = AppMode.SCAN
        self._mic = MicController(engine, self)
        self._packs = ExpertPackStore()
        self._talk_recording = False

        self._live_tap = LiveTranscriptTap(
            stt_paths or SttPaths("whisper-cli", "model.bin"),
            device=input_device,
        )
        self._live_tap.partial_text.connect(self._on_partial_transcript)

        self.setWindowTitle(assistant_name)
        self._apply_window_geometry()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(t.SPACE_MD, t.SPACE_XS, t.SPACE_MD, t.SPACE_MD)
        root.setSpacing(t.SPACE_SM)

        self._header = InstrumentHeader()
        self._header.menu_clicked.connect(self._open_history_placeholder)
        self._header.settings_clicked.connect(self._open_settings)
        root.addWidget(self._header)

        self._pack_strip = ExpertPackStrip()
        self._pack_strip.switch_requested.connect(self._switch_expert_pack)
        self._pack_strip.set_pack(self._packs.active)
        root.addWidget(self._pack_strip)

        self._stack = QStackedWidget()
        self._scan = ScanScreen(self._uploads_dir())
        self._talk = TalkScreen()
        self._chat = TouchChatView(assistant_name)
        self._stack.addWidget(self._scan)
        self._stack.addWidget(self._talk)
        self._stack.addWidget(self._chat)
        root.addWidget(self._stack, stretch=1)

        self._mode_switch = ModeSwitcher()
        self._mode_switch.mode_changed.connect(self._on_mode_changed)
        root.addWidget(self._mode_switch)

        # Scan
        self._scan.capture_requested.connect(self._on_capture_clicked)
        self._scan.gallery_requested.connect(self._open_history_placeholder)
        self._scan.camera_shell.camera.capture_finished.connect(self._on_capture_finished)
        self._scan.camera_shell.camera.capture_failed.connect(self._on_capture_failed)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._on_capture_clicked)

        # Talk
        self._talk.mic_tapped.connect(self._on_talk_mic_tapped)
        self._talk.mic_long_pressed.connect(self._on_talk_mic_long_pressed)
        self._talk.end_conversation.connect(self._on_end_conversation)
        self._talk.send_transcript.connect(self._on_talk_send)

        # Chat
        self._chat.back_button.clicked.connect(lambda: self._mode_switch.set_mode(AppMode.SCAN))
        self._chat.send_requested.connect(self._on_chat_send)

        # Mic controller
        self._mic.state_changed.connect(self._on_touch_state)
        self._mic.status_message.connect(self._on_voice_hint)
        self._mic.answer_ready.connect(self._on_answer_ready)
        self._mic.error_occurred.connect(self._on_mic_error)
        self._mic.transcript_ready.connect(self._on_engine_transcript)

        self._on_touch_state(TouchInteractionState.READY)
        QTimer.singleShot(0, self._scan.start_camera)

    def _uploads_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "data" / "uploads"

    def _apply_window_geometry(self) -> None:
        if self._screen_inches <= 5:
            self.resize(800, 480)
            self.setMinimumSize(640, 400)
        else:
            self.resize(800, 480)
            self.setMinimumSize(720, 440)

    def _active_ai_panel(self):
        if self._app_mode == AppMode.TALK:
            return self._talk.ai_panel
        return self._scan.ai_panel

    def _pack_source_label(self) -> str:
        pack = self._packs.active
        return f"{pack.name} · v{pack.version} · {pack.source}"

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def _on_mode_changed(self, mode: AppMode) -> None:
        if self._mic.conversation_active or self._talk_recording:
            self._mode_switch.set_mode(self._app_mode)
            return
        self._app_mode = mode
        if mode == AppMode.SCAN:
            self._stack.setCurrentWidget(self._scan)
            self._scan.start_camera()
        elif mode == AppMode.TALK:
            self._stack.setCurrentWidget(self._talk)
            self._scan.stop_camera()
        else:
            self._stack.setCurrentWidget(self._chat)
            self._scan.stop_camera()
            self._chat.load_history(self._engine.get_history())

    # ------------------------------------------------------------------
    # Talk / voice
    # ------------------------------------------------------------------

    def _on_talk_mic_tapped(self) -> None:
        if self._mic.conversation_active:
            return
        if self._talk_recording:
            self._stop_talk_recording()
        elif self._touch_state in (TouchInteractionState.READY, TouchInteractionState.ERROR):
            self._start_talk_recording()

    def _on_talk_mic_long_pressed(self) -> None:
        if self._mic.can_start_interaction():
            self._talk.clear_transcript()
            self._active_ai_panel().clear_answer()
            self._mic.enter_conversation_mode()
            self._start_live_tap()

    def _start_talk_recording(self) -> None:
        self._talk_recording = True
        self._talk.clear_transcript()
        self._active_ai_panel().clear_answer()
        self._live_tap.start()
        self._talk.set_recording(True)
        self._on_touch_state(TouchInteractionState.ONE_SHOT_RECORDING)

    def _start_live_tap(self) -> None:
        if not self._live_tap.is_active:
            self._live_tap.start()

    def _stop_live_tap(self) -> None:
        if self._live_tap.is_active:
            self._live_tap.cancel()

    def _stop_talk_recording(self) -> None:
        self._talk_recording = False
        self._talk.set_recording(False)
        wav_path = self._live_tap.stop()
        if wav_path is None:
            guess = self._live_tap.current_guess()
            if guess:
                self._talk.finalize_transcript(guess)
            self._on_touch_state(TouchInteractionState.READY)
            return
        worker = PartialTranscribeWorker(wav_path, self._live_tap.paths)
        worker.finished_text.connect(self._talk.finalize_transcript)
        worker.finished.connect(lambda: setattr(self, "_finalize_worker", None))
        self._finalize_worker = worker
        worker.start()
        self._on_touch_state(TouchInteractionState.READY)

    def _on_partial_transcript(self, text: str) -> None:
        if self._app_mode == AppMode.TALK:
            self._talk.set_partial_text(text)

    def _on_engine_transcript(self, text: str) -> None:
        if self._app_mode == AppMode.TALK:
            self._talk.finalize_transcript(text)

    def _on_end_conversation(self) -> None:
        self._stop_live_tap()
        self._mic.exit_conversation_mode()

    def _on_talk_send(self, text: str) -> None:
        if self._mic.is_busy() or self._worker is not None:
            return
        self._active_ai_panel().clear_answer()
        worker = VoiceTextSendWorker(self._engine, text)
        worker.state_changed.connect(self._on_voice_engine_state)
        worker.finished_ok.connect(self._on_voice_text_finished)
        worker.failed.connect(self._on_mic_error)
        worker.finished.connect(lambda: setattr(self, "_worker", None))
        self._worker = worker
        worker.start()

    def _on_voice_text_finished(self, result: TurnResult | None) -> None:
        if result and result.reply_text:
            ctx = self._engine.get_visual_context()
            caption = result.image_caption or (ctx.caption if ctx else None)
            self._active_ai_panel().set_answer(
                result.reply_text,
                image_caption=caption,
                source=self._pack_source_label(),
            )
        self._talk.clear_transcript()
        self._on_touch_state(TouchInteractionState.READY)

    def _on_voice_engine_state(self, state_value: str) -> None:
        engine_state = AppState(state_value)
        if engine_state == AppState.THINKING:
            self._on_touch_state(TouchInteractionState.THINKING)
        elif engine_state == AppState.SPEAKING:
            self._on_touch_state(TouchInteractionState.SPEAKING)

    def _on_mic_error(self, message: str) -> None:
        logger.error("Mic error: %s", message)
        self._active_ai_panel().set_error(message[:80] if message else "Couldn't catch that.")
        self._on_touch_state(TouchInteractionState.ERROR)

    def _on_voice_hint(self, message: str) -> None:
        if self._mic.conversation_active and self._app_mode == AppMode.TALK:
            self._talk.ai_panel.set_voice_mode_label(message)

    def _on_answer_ready(self, result: TurnResult) -> None:
        ctx = self._engine.get_visual_context()
        caption = result.image_caption or (ctx.caption if ctx else None)
        panel = self._talk.ai_panel if self._mic.conversation_active else self._active_ai_panel()
        panel.set_answer(
            result.reply_text or "",
            image_caption=caption,
            source=self._pack_source_label(),
        )

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def _on_chat_send(self, text: str) -> None:
        if self._worker is not None:
            return
        self._chat.append_user(text)
        self._chat.start_assistant()
        self._chat.set_input_enabled(False)
        worker = TextMessageWorker(self._engine, text)
        worker.state_changed.connect(self._on_chat_engine_state)
        worker.finished_ok.connect(self._on_chat_finished)
        worker.failed.connect(self._on_chat_failed)
        worker.finished.connect(lambda: setattr(self, "_worker", None))
        self._worker = worker
        worker.start()

    def _on_chat_engine_state(self, state_value: str) -> None:
        if AppState(state_value) == AppState.THINKING:
            self._on_touch_state(TouchInteractionState.THINKING)

    def _on_chat_finished(self, result: TurnResult | None) -> None:
        self._chat.set_input_enabled(True)
        if result and result.reply_text:
            self._chat.finalize_assistant(result.reply_text)
        else:
            self._chat.remove_empty_assistant()
        self._on_touch_state(TouchInteractionState.READY)

    def _on_chat_failed(self, message: str) -> None:
        self._chat.set_input_enabled(True)
        self._chat.remove_empty_assistant()
        self._chat.finalize_assistant(f"Error: {message[:80]}")
        self._on_touch_state(TouchInteractionState.ERROR)

    # ------------------------------------------------------------------
    # Capture / photo
    # ------------------------------------------------------------------

    def _on_capture_clicked(self) -> None:
        if self._app_mode != AppMode.SCAN:
            return
        if self._touch_state != TouchInteractionState.READY or self._mic.is_busy():
            return
        self._on_touch_state(TouchInteractionState.CAPTURING)
        self._scan.camera_shell.set_capturing(True)
        QTimer.singleShot(180, self._scan.camera_shell.camera.capture_to_file)

    def _on_capture_finished(self, path: str) -> None:
        self._scan.camera_shell.set_capturing(False)
        worker = PhotoAttachWorker(self._engine, path)
        worker.state_changed.connect(self._on_photo_engine_state)
        worker.photo_ready.connect(self._on_photo_ready)
        worker.failed.connect(self._on_photo_failed)
        worker.finished.connect(lambda: setattr(self, "_worker", None))
        self._worker = worker
        worker.start()

    def _on_capture_failed(self, message: str) -> None:
        self._scan.camera_shell.set_capturing(False)
        self._scan.ai_panel.set_error(message)
        self._on_touch_state(TouchInteractionState.ERROR)

    def _on_photo_ready(self, _path: str, caption: str) -> None:
        self._engine.record_photo_message(caption)
        self._scan.ai_panel.set_answer("", image_caption=caption, source="Vision · On-device")
        worker = PhotoGreetingWorker(self._engine)
        worker.state_changed.connect(self._on_photo_engine_state)
        worker.finished_ok.connect(self._on_photo_greeting_finished)
        worker.failed.connect(self._on_photo_failed)
        worker.finished.connect(lambda: setattr(self, "_worker", None))
        self._worker = worker
        worker.start()

    def _on_photo_greeting_finished(self, result: TurnResult | None) -> None:
        if result and result.reply_text:
            ctx = self._engine.get_visual_context()
            self._scan.ai_panel.set_answer(
                result.reply_text,
                image_caption=ctx.caption if ctx else None,
                source=self._pack_source_label(),
            )
        self._on_touch_state(TouchInteractionState.READY)

    def _on_photo_failed(self, message: str) -> None:
        self._scan.ai_panel.set_error(message[:80])
        self._on_touch_state(TouchInteractionState.ERROR)

    def _on_photo_engine_state(self, state_value: str) -> None:
        engine_state = AppState(state_value)
        if engine_state == AppState.ANALYZING:
            self._on_touch_state(TouchInteractionState.TRANSCRIBING)
        elif engine_state == AppState.THINKING:
            self._on_touch_state(TouchInteractionState.THINKING)

    # ------------------------------------------------------------------
    # Expert pack / settings
    # ------------------------------------------------------------------

    def _switch_expert_pack(self) -> None:
        if self._mic.conversation_active or self._talk_recording:
            return
        self._on_touch_state(TouchInteractionState.LOADING_PACK)
        sheet = ExpertPackSheet(self._packs, parent=self)
        if sheet.exec():
            self._pack_strip.set_pack(self._packs.active)
        self._on_touch_state(TouchInteractionState.READY)

    def _open_settings(self) -> None:
        if self._mic.conversation_active:
            return
        SettingsSheet(self._engine, self._assistant_name, parent=self).exec()

    def _open_history_placeholder(self) -> None:
        if self._app_mode != AppMode.CHAT:
            self._mode_switch.set_mode(AppMode.CHAT)

    # ------------------------------------------------------------------
    # Touch UI state
    # ------------------------------------------------------------------

    def _on_touch_state(
        self,
        state: TouchInteractionState,
        override: str | None = None,
    ) -> None:
        self._touch_state = state
        self._header.set_state(state, override=override)
        idle = state == TouchInteractionState.READY and not self._mic.conversation_active
        self._header.set_idle_breathing(idle)

        in_conversation = self._mic.conversation_active
        if self._app_mode == AppMode.TALK:
            self._talk.set_conversation_mode(in_conversation)
            self._talk.set_thinking(
                state in (TouchInteractionState.THINKING, TouchInteractionState.TRANSCRIBING)
            )
            self._talk.set_speaking(state == TouchInteractionState.SPEAKING)
            voice_label = (override or STATE_LABELS.get(state, "")) if in_conversation else None
            self._talk.ai_panel.set_voice_mode_label(voice_label)
            if in_conversation:
                if state == TouchInteractionState.CONVERSATION_LISTENING:
                    self._start_live_tap()
                elif state in (
                    TouchInteractionState.THINKING,
                    TouchInteractionState.SPEAKING,
                    TouchInteractionState.TRANSCRIBING,
                ):
                    self._stop_live_tap()
            elif state == TouchInteractionState.ONE_SHOT_RECORDING:
                self._talk.set_recording(True)

        if self._app_mode == AppMode.SCAN:
            listening = state == TouchInteractionState.ONE_SHOT_RECORDING
            self._scan.camera_shell.set_listening(listening)
            self._scan.camera_shell.set_capturing(state == TouchInteractionState.CAPTURING)

        ready = state in (TouchInteractionState.READY, TouchInteractionState.ERROR)
        self._scan.set_capture_enabled(
            ready and self._app_mode == AppMode.SCAN and not in_conversation
        )
        self._mode_switch.setEnabled(not self._talk_recording and not in_conversation)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._mic.exit_conversation_mode()
        self._live_tap.cancel()
        self._scan.stop_camera()
        super().closeEvent(event)
