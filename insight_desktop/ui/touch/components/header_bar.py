"""Premium instrumentation header for Offgrid Minds."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.touch import tokens as t
from ui.touch.components.micro_animations import BreathingRingWidget
from ui.touch.interaction_state import HEADER_LABELS, STATE_COLORS, TouchInteractionState


class RingLogoWidget(QWidget):
    """Glowing Offgrid Minds ring with optional idle breathing."""

    def __init__(self, size: int = 36, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self._breath = BreathingRingWidget(size, self)
        self._breath.move(0, 0)

    def set_breathing(self, active: bool) -> None:
        self._breath.set_breathing(active)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        outer = self._size * 0.44
        inner = self._size * 0.30
        ring = QPen(QColor(t.ACCENT))
        ring.setWidthF(2.5)
        p.setPen(ring)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(int(cx - outer), int(cy - outer), int(outer * 2), int(outer * 2))
        core = QPen(QColor(t.ACCENT_DIM))
        core.setWidthF(1.5)
        p.setPen(core)
        p.drawEllipse(int(cx - inner), int(cy - inner), int(inner * 2), int(inner * 2))
        p.end()


class InstrumentHeader(QWidget):
    menu_clicked = Signal()
    settings_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("instrumentHeader")
        self.setFixedHeight(t.MIN_TOUCH)

        root = QHBoxLayout(self)
        root.setContentsMargins(t.SPACE_MD, t.SPACE_XS, t.SPACE_MD, t.SPACE_XS)
        root.setSpacing(t.SPACE_MD)

        # Brand block
        brand_row = QHBoxLayout()
        brand_row.setSpacing(t.SPACE_SM)
        self._logo = RingLogoWidget(36)
        brand_row.addWidget(self._logo)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        self._brand = QLabel("OFFGRID MINDS")
        self._brand.setObjectName("brandName")
        self._tagline = QLabel("Knowledge Anywhere")
        self._tagline.setObjectName("brandTagline")
        brand_text.addWidget(self._brand)
        brand_text.addWidget(self._tagline)
        brand_row.addLayout(brand_text)
        root.addLayout(brand_row)

        root.addStretch(1)

        # Instrument cluster (right)
        cluster = QHBoxLayout()
        cluster.setSpacing(t.SPACE_SM)

        self._status = QWidget()
        self._status.setObjectName("headerStatus")
        status_row = QHBoxLayout(self._status)
        status_row.setContentsMargins(10, 4, 12, 4)
        status_row.setSpacing(8)
        self._status_dot = QLabel()
        self._status_dot.setObjectName("headerStatusDot")
        self._status_dot.setFixedSize(8, 8)
        self._status_label = QLabel("READY")
        self._status_label.setObjectName("headerStatusLabel")
        status_row.addWidget(self._status_dot)
        status_row.addWidget(self._status_label)
        cluster.addWidget(self._status)

        self._model_chip = QLabel("MODEL")
        self._model_chip.setObjectName("headerChip")
        self._model_chip.setToolTip("On-device model loaded")
        cluster.addWidget(self._model_chip)

        self._battery_chip = QLabel(self._read_battery())
        self._battery_chip.setObjectName("headerChip")
        cluster.addWidget(self._battery_chip)

        menu_btn = QPushButton("☰")
        menu_btn.setObjectName("headerIconBtn")
        menu_btn.setToolTip("Menu")
        menu_btn.clicked.connect(self.menu_clicked.emit)
        cluster.addWidget(menu_btn)

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("headerIconBtn")
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self.settings_clicked.emit)
        cluster.addWidget(settings_btn)

        root.addLayout(cluster)
        self.set_state(TouchInteractionState.READY)

    def set_state(self, state: TouchInteractionState, override: str | None = None) -> None:
        label = override or HEADER_LABELS.get(state, state.value.upper())
        color = STATE_COLORS.get(state, t.TEXT_TERTIARY)
        self._status_label.setText(label)
        self._status_dot.setStyleSheet(f"background:{color}; border-radius:4px;")

    def set_idle_breathing(self, active: bool) -> None:
        if isinstance(self._logo, RingLogoWidget):
            self._logo.set_breathing(active)

    @staticmethod
    def _read_battery() -> str:
        supply = Path("/sys/class/power_supply")
        if not supply.is_dir():
            return "PWR"
        for bat in sorted(supply.glob("BAT*")):
            cap = bat / "capacity"
            if cap.is_file():
                try:
                    pct = int(cap.read_text().strip())
                    return f"{pct}%"
                except ValueError:
                    pass
        return "PWR"
