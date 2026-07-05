"""The main application window."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from engine.interface import InsightEngine
from engine.types import AppState, TurnResult
from ui.chat_widgets import ChatTranscript
from ui.inspector_panel import InspectorPanel
from ui import theme
from ui.workers import BaseEngineWorker, TextMessageWorker, VoiceUtteranceWorker

logger = logging.getLogger("insight.ui")

_ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "icon.png"


class MainWindow(QMainWindow):
    def __init__(self, engine: InsightEngine, assistant_name: str = "Insight") -> None:
        super().__init__()
        self._engine = engine
        self._worker: BaseEngineWorker | None = None
        self._current_state = AppState.IDLE
        self._assistant_name = assistant_name

        self.setWindowTitle(assistant_name)
        self.resize(1200, 780)
        self.setMinimumSize(900, 580)

        if _ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(_ICON_PATH)))

        self._build_ui()
        self._transcript.load_history(self._engine.get_history())
        self._apply_state(AppState.IDLE)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        root_layout.addWidget(splitter, stretch=1)

        chat_panel = QWidget()
        chat_panel.setObjectName("chatPanel")
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.setContentsMargins(20, 18, 20, 18)
        chat_layout.setSpacing(12)

        self._transcript = ChatTranscript(assistant_name=self._assistant_name)
        chat_layout.addWidget(self._transcript, stretch=1)

        input_bar = QWidget()
        input_bar.setObjectName("inputBar")
        input_row = QHBoxLayout(input_bar)
        input_row.setContentsMargins(8, 6, 8, 6)
        input_row.setSpacing(8)

        self._input_box = QLineEdit()
        self._input_box.setPlaceholderText(f"Ask {self._assistant_name} anything…")
        self._input_box.returnPressed.connect(self._on_send_clicked)
        input_row.addWidget(self._input_box, stretch=1)

        self._mic_btn = QPushButton("●")
        self._mic_btn.setObjectName("micButton")
        self._mic_btn.setToolTip("Press to talk")
        self._mic_btn.clicked.connect(self._on_mic_clicked)
        input_row.addWidget(self._mic_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("ghostButton")
        self._stop_btn.setToolTip("Cancel current action")
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        input_row.addWidget(self._stop_btn)

        self._send_btn = QPushButton("Send")
        self._send_btn.setObjectName("primaryButton")
        self._send_btn.clicked.connect(self._on_send_clicked)
        input_row.addWidget(self._send_btn)

        chat_layout.addWidget(input_bar)
        splitter.addWidget(chat_panel)

        self._inspector = InspectorPanel(self._engine)
        self._inspector.setObjectName("inspectorPanel")
        self._inspector.session_reset.connect(self._on_session_reset)
        splitter.addWidget(self._inspector)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([720, 420])

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("headerBar")
        header.setFixedHeight(60)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(12)

        logo = QLabel()
        logo.setFixedSize(36, 36)
        if _ICON_PATH.exists():
            pixmap = QPixmap(str(_ICON_PATH)).scaled(
                36, 36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo.setPixmap(pixmap)
        else:
            logo.setText("I")
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo.setStyleSheet(
                f"background:{theme.ACCENT}; color:white; border-radius:10px; "
                "font-weight:700; font-size:18px;"
            )
        layout.addWidget(logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel(self._assistant_name)
        title.setObjectName("titleLabel")
        subtitle = QLabel("Offline · Local · Private")
        subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        layout.addStretch(1)

        status_pill = QWidget()
        status_pill.setObjectName("statusPill")
        status_row = QHBoxLayout(status_pill)
        status_row.setContentsMargins(10, 4, 12, 4)
        status_row.setSpacing(8)

        self._status_dot = QLabel()
        self._status_dot.setObjectName("statusDot")
        self._status_dot.setFixedSize(8, 8)
        status_row.addWidget(self._status_dot)

        self._status_label = QLabel(theme.STATUS_LABELS["idle"])
        self._status_label.setStyleSheet(f"font-size:12px; font-weight:500; color:{theme.INK_SECONDARY};")
        status_row.addWidget(self._status_label)

        layout.addWidget(status_pill)

        return header

    def _on_send_clicked(self) -> None:
        if self._current_state != AppState.IDLE:
            return
        text = self._input_box.text().strip()
        if not text:
            return

        self._input_box.clear()
        self._transcript.add_user_message(text)
        self._transcript.start_assistant_message()

        worker = TextMessageWorker(self._engine, text)
        self._wire_worker(worker)
        worker.start()

    def _on_mic_clicked(self) -> None:
        if self._current_state == AppState.IDLE:
            self._engine.start_recording(on_state=self._on_engine_state)
        elif self._current_state == AppState.LISTENING:
            worker = VoiceUtteranceWorker(self._engine)
            worker.transcript_ready.connect(self._on_transcript_ready)
            self._wire_worker(worker)
            worker.start()

    def _on_transcript_ready(self, text: str) -> None:
        self._transcript.add_user_message(text)
        self._transcript.start_assistant_message()

    def _on_stop_clicked(self) -> None:
        if self._current_state == AppState.LISTENING:
            self._engine.cancel_recording(on_state=self._on_engine_state)
        else:
            self._engine.cancel_current()

    def _wire_worker(self, worker: BaseEngineWorker) -> None:
        worker.token_received.connect(self._transcript.append_to_last_assistant)
        worker.state_changed.connect(self._on_engine_state_str)
        worker.finished_ok.connect(self._on_turn_finished)
        worker.failed.connect(self._on_turn_failed)
        worker.finished.connect(lambda: setattr(self, "_worker", None))
        self._worker = worker

    def _on_engine_state(self, state: AppState) -> None:
        self._apply_state(state)

    def _on_engine_state_str(self, state_value: str) -> None:
        self._apply_state(AppState(state_value))

    def _on_turn_finished(self, result: TurnResult | None) -> None:
        if result is None:
            self._transcript.remove_last_assistant_if_empty()
        else:
            self._transcript.finalize_last_assistant(result.reply_text, cancelled=result.cancelled)
            self._inspector.show_turn_debug(result.assembled_prompt_debug, result.latency_ms, result.cancelled)
        self._inspector.refresh()
        self._apply_state(AppState.IDLE)

    def _on_turn_failed(self, message: str) -> None:
        logger.error("Turn failed: %s", message)
        self._transcript.remove_last_assistant_if_empty()
        self._apply_state(AppState.ERROR, status_override=f"Error — {message[:80]}")

    def _on_session_reset(self) -> None:
        self._transcript.clear_transcript()

    def _apply_state(self, state: AppState, status_override: str | None = None) -> None:
        self._current_state = state
        label = status_override or theme.STATUS_LABELS.get(state.value, state.value)
        self._status_label.setText(label)

        dot_color = theme.STATUS_COLORS.get(state.value, theme.MUTED_LIGHT)
        self._status_dot.setStyleSheet(
            f"border-radius:4px; background:{dot_color}; min-width:8px; max-width:8px;"
        )

        is_idle = state == AppState.IDLE
        is_listening = state == AppState.LISTENING

        self._send_btn.setEnabled(is_idle)
        self._input_box.setEnabled(is_idle)
        self._mic_btn.setEnabled(is_idle or is_listening)
        self._mic_btn.setText("■" if is_listening else "●")
        self._mic_btn.setToolTip("Stop recording and send" if is_listening else "Press to talk")
        self._mic_btn.setProperty("recording", is_listening)
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)
        self._stop_btn.setEnabled(not is_idle)
