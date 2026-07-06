"""Dark-themed full-screen chat for touch / Pi."""

from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from storage.models import Message
from ui.touch import tokens as t


def _wrap(body: str) -> str:
    return (
        f'<div style="font-family:Inter,system-ui,sans-serif; font-size:13px; '
        f'line-height:1.5; color:{t.TEXT_PRIMARY};">{body}</div>'
    )


class TouchChatView(QWidget):
    """Full-screen keyboard conversation with persistent history."""

    send_requested = Signal(str)

    def __init__(self, assistant_name: str = "Offgrid Minds", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chatScreen")
        self._assistant_name = assistant_name

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(t.SPACE_SM)

        top = QHBoxLayout()
        self._back = QPushButton("← Camera")
        self._back.setObjectName("chatBackBtn")
        top.addWidget(self._back)
        title = QWidget()
        top.addStretch(1)
        root.addLayout(top)

        self._transcript = QTextEdit()
        self._transcript.setObjectName("chatTranscript")
        self._transcript.setReadOnly(True)
        self._transcript.setFrameStyle(0)
        root.addWidget(self._transcript, stretch=1)

        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setObjectName("chatInput")
        self._input.setPlaceholderText("Message…")
        self._input.setMinimumHeight(t.MIN_TOUCH)
        self._input.returnPressed.connect(self._send)
        input_row.addWidget(self._input, stretch=1)

        self._send = QPushButton("Send")
        self._send.setObjectName("chatSendBtn")
        self._send.setMinimumHeight(t.MIN_TOUCH)
        self._send.setMinimumWidth(72)
        self._send.clicked.connect(self._send)
        input_row.addWidget(self._send)
        root.addLayout(input_row)

        self._show_empty()

    @property
    def back_button(self) -> QPushButton:
        return self._back

    def load_history(self, messages: list[Message]) -> None:
        self._transcript.clear()
        if not messages:
            self._show_empty()
            return
        for msg in messages[-40:]:
            role = "You" if msg.role == "user" else self._assistant_name
            safe = html.escape(msg.content).replace("\n", "<br>")
            align = "right" if msg.role == "user" else "left"
            color = t.ACCENT if msg.role == "user" else t.TEXT_PRIMARY
            bubble_bg = t.SURFACE_RAISED if msg.role == "user" else t.SURFACE
            self._transcript.append(_wrap(
                f'<div style="text-align:{align}; margin:6px 0;">'
                f'<span style="display:inline-block; max-width:85%; padding:10px 14px; '
                f'border-radius:14px; background:{bubble_bg}; color:{color}; '
                f'border:1px solid {t.BORDER};">{safe}</span></div>'
            ))

    def append_user(self, text: str) -> None:
        safe = html.escape(text)
        self._transcript.append(_wrap(
            f'<div style="text-align:right; margin:6px 0;">'
            f'<span style="display:inline-block; max-width:85%; padding:10px 14px; '
            f'border-radius:14px; background:{t.SURFACE_RAISED}; color:{t.ACCENT}; '
            f'border:1px solid {t.BORDER};">{safe}</span></div>'
        ))
        self._scroll()

    def start_assistant(self) -> None:
        self._transcript.append(_wrap(
            f'<div style="margin:6px 0; color:{t.TEXT_TERTIARY};"><i>Thinking…</i></div>'
        ))
        self._scroll()

    def append_assistant_token(self, token: str) -> None:
        cursor = self._transcript.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self._scroll()

    def finalize_assistant(self, text: str) -> None:
        cursor = self._transcript.textCursor()
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()
        safe = html.escape(text).replace("\n", "<br>")
        self._transcript.append(_wrap(
            f'<div style="text-align:left; margin:6px 0;">'
            f'<span style="display:inline-block; max-width:85%; padding:10px 14px; '
            f'border-radius:14px; background:{t.SURFACE}; color:{t.TEXT_PRIMARY}; '
            f'border:1px solid {t.BORDER};">{safe}</span></div>'
        ))
        self._scroll()

    def remove_empty_assistant(self) -> None:
        cursor = self._transcript.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        block = cursor.block().text()
        if "Thinking" in block:
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()

    def set_input_enabled(self, enabled: bool) -> None:
        self._input.setEnabled(enabled)
        self._send.setEnabled(enabled)

    def _send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.send_requested.emit(text)

    def _show_empty(self) -> None:
        self._transcript.setHtml(_wrap(
            f'<div style="text-align:center; padding:48px 24px; color:{t.TEXT_TERTIARY};">'
            f'<div style="font-size:15px; font-weight:600; color:{t.TEXT_SECONDARY}; '
            f'margin-bottom:8px;">Chat with {html.escape(self._assistant_name)}</div>'
            f'Fully offline. Your conversation stays on this device.</div>'
        ))

    def _scroll(self) -> None:
        bar = self._transcript.verticalScrollBar()
        bar.setValue(bar.maximum())
