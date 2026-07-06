"""Always-visible Expert Pack strip with one-tap switching."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from ui.touch import tokens as t
from ui.touch.expert_packs import ExpertPack


class ExpertPackStrip(QWidget):
    switch_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("expertPackStrip")
        self.setFixedHeight(40)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(t.SPACE_SM)

        self._label = QLabel("EXPERT PACK")
        self._label.setObjectName("expertPackLabel")
        row.addWidget(self._label)

        self._name = QLabel("General Field")
        self._name.setObjectName("expertPackName")
        row.addWidget(self._name)

        self._meta = QLabel("v1.0 · Verified")
        self._meta.setObjectName("expertPackMeta")
        row.addWidget(self._meta, stretch=1)

        self._switch = QPushButton("Switch")
        self._switch.setObjectName("expertPackSwitchBtn")
        self._switch.clicked.connect(self.switch_requested.emit)
        row.addWidget(self._switch)

    def set_pack(self, pack: ExpertPack) -> None:
        self._name.setText(pack.name)
        self._meta.setText(f"v{pack.version} · {pack.trust} · {pack.source}")
