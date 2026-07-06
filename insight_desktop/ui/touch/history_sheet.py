"""Simple history sheet for the touch UI."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QListWidget, QPushButton, QVBoxLayout

from engine.interface import InsightEngine


class HistorySheet(QDialog):
    def __init__(self, engine: InsightEngine, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("touchSheet")
        self.setWindowTitle("History")
        self.resize(420, 520)

        layout = QVBoxLayout(self)
        title = QLabel("Recent messages")
        title.setObjectName("sheetTitle")
        layout.addWidget(title)

        self._list = QListWidget()
        layout.addWidget(self._list, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondaryButton")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        for msg in engine.get_history()[-20:]:
            prefix = "You" if msg.role == "user" else "Insight"
            snippet = msg.content.replace("\n", " ")[:120]
            self._list.addItem(f"{prefix}: {snippet}")

        if self._list.count() == 0:
            self._list.addItem("No messages yet.")
