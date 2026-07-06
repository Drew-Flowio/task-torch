"""Single-line text prompt with send button."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget

from ui.touch import tokens as t


class PromptBar(QWidget):
    send_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("promptBar")
        self.setFixedHeight(t.MIN_TOUCH)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(t.SPACE_SM)

        self._input = QLineEdit()
        self._input.setObjectName("promptInput")
        self._input.setPlaceholderText("Ask anything…")
        self._input.returnPressed.connect(self._on_send)
        row.addWidget(self._input, stretch=1)

        self._send = QPushButton("→")
        self._send.setObjectName("promptSendBtn")
        self._send.setFixedSize(t.MIN_TOUCH, t.MIN_TOUCH)
        self._send.clicked.connect(self._on_send)
        row.addWidget(self._send)

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self.send_clicked.emit(text)

    def set_enabled(self, enabled: bool) -> None:
        self._input.setEnabled(enabled)
        self._send.setEnabled(enabled)

    def clear(self) -> None:
        self._input.clear()
