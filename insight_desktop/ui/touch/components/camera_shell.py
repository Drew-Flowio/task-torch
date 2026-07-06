"""Camera view with instrumentation overlays — no changes to capture pipeline."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.touch import tokens as t
from ui.touch.camera_preview import CameraPreviewWidget


class CornerBracketOverlay(QWidget):
    """Subtle corner brackets — no thick borders."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._accent = QColor(t.BORDER)

    def set_active(self, active: bool) -> None:
        self._accent = QColor(t.ACCENT if active else t.BORDER)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._accent)
        pen.setWidthF(1.5)
        p.setPen(pen)
        w, h = self.width(), self.height()
        arm = min(22, w // 8, h // 8)
        margin = 8
        corners = (
            (margin, margin, margin + arm, margin, margin, margin + arm),
            (w - margin, margin, w - margin - arm, margin, w - margin, margin + arm),
            (margin, h - margin, margin + arm, h - margin, margin, h - margin - arm),
            (w - margin, h - margin, w - margin - arm, h - margin, w - margin, h - margin - arm),
        )
        for x1, y1, x2, y2, x3, y3 in corners:
            p.drawLine(x1, y1, x2, y2)
            p.drawLine(x1, y1, x3, y3)
        p.end()


class CameraShell(QWidget):
    """70% camera column: live feed, overlays, prompt slot below."""

    photo_clicked = Signal()
    gallery_clicked = Signal()

    def __init__(self, uploads_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cameraShell")

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(t.SPACE_SM)

        # Camera + overlay stack
        self._viewport = QWidget()
        self._viewport.setObjectName("cameraViewport")
        grid = QGridLayout(self._viewport)
        grid.setContentsMargins(0, 0, 0, 0)

        self.camera = CameraPreviewWidget(uploads_dir)
        self._overlay = CornerBracketOverlay()
        grid.addWidget(self.camera, 0, 0)
        grid.addWidget(self._overlay, 0, 0)

        # HUD layer
        hud = QWidget(self._viewport)
        hud.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        hud_layout = QVBoxLayout(hud)
        hud_layout.setContentsMargins(10, 8, 10, 8)

        top = QHBoxLayout()
        self._live = QLabel("LIVE")
        self._live.setObjectName("liveBadge")
        top.addWidget(self._live)
        top.addStretch(1)
        self._zoom = QLabel("1.0×")
        self._zoom.setObjectName("zoomBadge")
        top.addWidget(self._zoom)
        hud_layout.addLayout(top)
        hud_layout.addStretch(1)

        bottom = QHBoxLayout()
        self._photo_btn = QPushButton("PHOTO")
        self._photo_btn.setObjectName("cameraHudBtn")
        self._photo_btn.clicked.connect(self.photo_clicked.emit)
        self._gallery_btn = QPushButton("GALLERY")
        self._gallery_btn.setObjectName("cameraHudBtn")
        self._gallery_btn.clicked.connect(self.gallery_clicked.emit)
        bottom.addWidget(self._photo_btn)
        bottom.addStretch(1)
        bottom.addWidget(self._gallery_btn)
        hud_layout.addLayout(bottom)

        grid.addWidget(hud, 0, 0)

        col.addWidget(self._viewport, stretch=1)

        # Prompt bar slot (filled by parent)
        self._prompt_slot = QWidget()
        self._prompt_slot.setObjectName("promptSlot")
        prompt_lay = QVBoxLayout(self._prompt_slot)
        prompt_lay.setContentsMargins(0, 0, 0, 0)
        col.addWidget(self._prompt_slot)

    def prompt_container(self) -> QWidget:
        return self._prompt_slot

    def set_prompt_bar(self, widget: QWidget) -> None:
        lay = self._prompt_slot.layout()
        if lay is not None:
            lay.addWidget(widget)

    def set_listening(self, active: bool) -> None:
        self._overlay.set_active(active)
        self.camera.set_listening(False)
        self.camera.set_conversation(False)

    def set_conversation(self, active: bool) -> None:
        self._overlay.set_active(active)
        self.camera.set_listening(False)
        self.camera.set_conversation(False)

    def set_capturing(self, active: bool) -> None:
        self.camera.set_capturing(active)
        self._overlay.set_active(active)
