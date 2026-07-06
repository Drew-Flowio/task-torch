"""Talk mode — live transcription + voice interaction."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.touch import tokens as t
from ui.touch.components.micro_animations import ScanPulseWidget, WaveformBar
from ui.touch.mic_button import MicButton
from ui.touch.widgets import AiResponsePanel


class TalkScreen(QWidget):
    mic_tapped = Signal()
    mic_long_pressed = Signal()
    end_conversation = Signal()
    send_transcript = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("talkScreen")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(t.SPACE_MD)

        left = QVBoxLayout()
        left.setSpacing(t.SPACE_SM)

        voice_header = QHBoxLayout()
        self._voice_label = QLabel("VOICE")
        self._voice_label.setObjectName("talkSectionTitle")
        voice_header.addWidget(self._voice_label)
        self._scan_pulse = ScanPulseWidget()
        voice_header.addWidget(self._scan_pulse)
        self._waveform = WaveformBar()
        voice_header.addWidget(self._waveform)
        voice_header.addStretch(1)
        left.addLayout(voice_header)

        self._transcript = QPlainTextEdit()
        self._transcript.setObjectName("liveTranscript")
        self._transcript.setPlaceholderText("Speak naturally. Words appear as they are recognized…")
        self._transcript.setMinimumHeight(120)
        left.addWidget(self._transcript, stretch=2)

        mic_row = QHBoxLayout()
        mic_row.addStretch(1)
        self._mic = MicButton()
        self._mic.setFixedSize(t.LARGE_TOUCH, t.LARGE_TOUCH)
        self._mic.tapped.connect(self.mic_tapped.emit)
        self._mic.long_pressed.connect(self.mic_long_pressed.emit)
        mic_row.addWidget(self._mic)

        self._send = QPushButton("Send")
        self._send.setObjectName("talkSendBtn")
        self._send.setMinimumHeight(t.MIN_TOUCH)
        self._send.hide()
        self._send.clicked.connect(self._on_send)
        mic_row.addWidget(self._send)

        self._end = QPushButton("End")
        self._end.setObjectName("micEndBtn")
        self._end.hide()
        self._end.clicked.connect(self.end_conversation.emit)
        mic_row.addWidget(self._end)

        mic_row.addStretch(1)
        left.addLayout(mic_row)

        hint = QLabel("Tap · single question   ·   Hold · conversation")
        hint.setObjectName("talkHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(hint)

        root.addLayout(left, stretch=3)

        self._ai = AiResponsePanel()
        root.addWidget(self._ai, stretch=2)

    @property
    def ai_panel(self) -> AiResponsePanel:
        return self._ai

    @property
    def mic_button(self) -> MicButton:
        return self._mic

    def set_partial_text(self, text: str) -> None:
        if not self._transcript.hasFocus():
            self._transcript.setPlainText(text)
            cursor = self._transcript.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self._transcript.setTextCursor(cursor)

    def append_partial_text(self, text: str) -> None:
        self._transcript.setPlainText(text)

    def transcript_text(self) -> str:
        return self._transcript.toPlainText().strip()

    def clear_transcript(self) -> None:
        self._transcript.clear()

    def set_recording(self, active: bool) -> None:
        self._mic.set_one_shot_recording(active)
        self._mic.set_listening_pulse(active)
        if not active:
            self._send.setVisible(bool(self.transcript_text()))

    def set_conversation_mode(self, active: bool) -> None:
        self._mic.set_conversation_mode(active)
        self._end.setVisible(active)

    def set_thinking(self, active: bool) -> None:
        self._scan_pulse.set_active(active)

    def set_speaking(self, active: bool) -> None:
        self._waveform.set_active(active)

    def set_send_visible(self, visible: bool) -> None:
        self._send.setVisible(visible)

    def finalize_transcript(self, text: str) -> None:
        self._transcript.setPlainText(text)
        self._send.show()

    def _on_send(self) -> None:
        text = self.transcript_text()
        if text:
            self.send_transcript.emit(text)
            self._send.hide()
