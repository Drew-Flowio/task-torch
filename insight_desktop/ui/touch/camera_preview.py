"""Live camera preview for the touch UI — lightweight, no extra effects."""

from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage
from PySide6.QtMultimedia import QCamera, QImageCapture, QMediaCaptureSession, QMediaDevices
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QFrame, QLabel, QStackedLayout, QVBoxLayout, QWidget


class CameraPreviewWidget(QFrame):
    """Embeds a live camera feed. Capture writes a JPEG to uploads_dir."""

    capture_finished = Signal(str)
    capture_failed = Signal(str)

    def __init__(self, uploads_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cameraFrame")
        self._uploads_dir = uploads_dir
        self._uploads_dir.mkdir(parents=True, exist_ok=True)
        self._camera: QCamera | None = None
        self._capture_session: QMediaCaptureSession | None = None
        self._image_capture: QImageCapture | None = None
        self._pending_path: Path | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedLayout()
        layout.addLayout(self._stack)

        self._placeholder = QLabel("Camera unavailable")
        self._placeholder.setObjectName("cameraPlaceholder")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stack.addWidget(self._placeholder)

        self._video = QVideoWidget()
        self._stack.addWidget(self._video)

        if QMediaDevices.videoInputs():
            self._init_camera()
        else:
            self._stack.setCurrentWidget(self._placeholder)

    def _init_camera(self) -> None:
        self._camera = QCamera(QMediaDevices.defaultVideoInput())
        self._capture_session = QMediaCaptureSession()
        self._capture_session.setCamera(self._camera)
        self._image_capture = QImageCapture()
        self._capture_session.setImageCapture(self._image_capture)
        self._capture_session.setVideoOutput(self._video)
        self._image_capture.imageCaptured.connect(self._on_image_captured)
        self._stack.setCurrentWidget(self._video)

    def start(self) -> None:
        if self._camera is not None:
            self._camera.start()

    def stop(self) -> None:
        if self._camera is not None:
            self._camera.stop()

    def capture_to_file(self) -> None:
        if self._image_capture is None:
            self.capture_failed.emit("No camera available.")
            return
        self._pending_path = self._uploads_dir / f"capture-{uuid.uuid4().hex}.jpg"
        self._image_capture.captureToFile(str(self._pending_path))

    def _on_image_captured(self, _id: int, image: QImage) -> None:
        if self._pending_path is None:
            return
        path = self._pending_path
        self._pending_path = None
        if image.isNull() or not image.save(str(path), "JPG"):
            path.unlink(missing_ok=True)
            self.capture_failed.emit("Could not save photo.")
            return
        self.capture_finished.emit(str(path))

    def set_listening(self, active: bool) -> None:
        self.setProperty("listening", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_capturing(self, active: bool) -> None:
        self.setProperty("capturing", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_conversation(self, active: bool) -> None:
        self.setProperty("conversation", active)
        self.style().unpolish(self)
        self.style().polish(self)
