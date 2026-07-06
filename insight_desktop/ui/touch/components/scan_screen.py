"""Scan mode — camera-primary field view."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ui.touch import tokens as t
from ui.touch.components.camera_shell import CameraShell
from ui.touch.widgets import AiResponsePanel


class ScanScreen(QWidget):
    capture_requested = Signal()
    gallery_requested = Signal()

    def __init__(self, uploads_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("scanScreen")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(t.SPACE_SM)

        split = QHBoxLayout()
        split.setSpacing(t.SPACE_MD)

        self._camera = CameraShell(uploads_dir)
        self._camera.photo_clicked.connect(self.capture_requested.emit)
        self._camera.gallery_clicked.connect(self.gallery_requested.emit)

        self._ai = AiResponsePanel()

        split.addWidget(self._camera, stretch=t.CAMERA_RATIO)
        split.addWidget(self._ai, stretch=t.AI_RATIO)
        root.addLayout(split, stretch=1)

        capture_row = QHBoxLayout()
        capture_row.addStretch(1)
        self._capture = QPushButton("CAPTURE")
        self._capture.setObjectName("scanCaptureBtn")
        self._capture.setMinimumSize(160, t.MIN_TOUCH)
        self._capture.clicked.connect(self.capture_requested.emit)
        capture_row.addWidget(self._capture)
        capture_row.addStretch(1)
        root.addLayout(capture_row)

    @property
    def camera_shell(self) -> CameraShell:
        return self._camera

    @property
    def ai_panel(self) -> AiResponsePanel:
        return self._ai

    def set_capture_enabled(self, enabled: bool) -> None:
        self._capture.setEnabled(enabled)
        self._camera.camera.setEnabled(enabled)

    def start_camera(self) -> None:
        self._camera.camera.start()

    def stop_camera(self) -> None:
        self._camera.camera.stop()
