"""Minimal settings sheet for the touch UI."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from engine.interface import InsightEngine


class SettingsSheet(QDialog):
    def __init__(self, engine: InsightEngine, assistant_name: str, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self.setObjectName("touchSheet")
        self.setWindowTitle("Settings")
        self.resize(420, 360)

        layout = QVBoxLayout(self)
        title = QLabel("Settings")
        title.setObjectName("sheetTitle")
        layout.addWidget(title)

        info = QLabel(
            f"{assistant_name} runs fully offline on this device.\n"
            "Use History for past messages. Reset clears the current session."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        reset_btn = QPushButton("Reset session")
        reset_btn.setObjectName("dangerButton")
        reset_btn.clicked.connect(self._reset)
        layout.addWidget(reset_btn)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondaryButton")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _reset(self) -> None:
        self._engine.reset_memory(scope="session")
        self.accept()
