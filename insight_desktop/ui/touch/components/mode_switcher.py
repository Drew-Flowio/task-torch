"""Scan | Talk | Chat mode switcher."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from ui.touch import tokens as t
from ui.touch.app_mode import AppMode


class ModeSwitcher(QWidget):
    mode_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("modeSwitcher")
        self.setFixedHeight(t.MIN_TOUCH)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(t.SPACE_XS)

        self._buttons: dict[AppMode, QPushButton] = {}
        for mode, label in (
            (AppMode.SCAN, "Scan"),
            (AppMode.TALK, "Talk"),
            (AppMode.CHAT, "Chat"),
        ):
            btn = QPushButton(label)
            btn.setObjectName("modeBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, m=mode: self._select(m))
            self._buttons[mode] = btn
            row.addWidget(btn, stretch=1)

        self._select(AppMode.SCAN, emit=False)

    def current_mode(self) -> AppMode:
        for mode, btn in self._buttons.items():
            if btn.isChecked():
                return mode
        return AppMode.SCAN

    def set_mode(self, mode: AppMode) -> None:
        self._select(mode, emit=False)

    def _select(self, mode: AppMode, emit: bool = True) -> None:
        for m, btn in self._buttons.items():
            btn.setChecked(m == mode)
            btn.setProperty("active", m == mode)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if emit:
            self.mode_changed.emit(mode)
