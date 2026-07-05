"""Attach or capture a photo for Insight to analyze."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage
from PySide6.QtMultimedia import QCamera, QImageCapture, QMediaCaptureSession, QMediaDevices
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class PhotoDialog(QDialog):
    """Pick an image file or snap one with the default camera."""

    def __init__(self, uploads_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add a photo")
        self.resize(640, 520)
        self._uploads_dir = uploads_dir
        self._uploads_dir.mkdir(parents=True, exist_ok=True)
        self._selected_path: str | None = None
        self._camera: QCamera | None = None
        self._capture_session: QMediaCaptureSession | None = None
        self._image_capture: QImageCapture | None = None
        self._pending_capture_path: Path | None = None

        layout = QVBoxLayout(self)
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, stretch=1)

        self._stack.addWidget(self._build_file_page())
        self._stack.addWidget(self._build_camera_page())

        mode_row = QHBoxLayout()
        self._file_mode_btn = QPushButton("Choose file")
        self._file_mode_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        self._camera_mode_btn = QPushButton("Use camera")
        self._camera_mode_btn.clicked.connect(self._enter_camera_mode)
        mode_row.addWidget(self._file_mode_btn)
        mode_row.addWidget(self._camera_mode_btn)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        if not QMediaDevices.videoInputs():
            self._camera_mode_btn.setEnabled(False)
            self._camera_mode_btn.setToolTip("No camera detected on this machine.")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_path(self) -> str | None:
        return self._selected_path

    def _build_file_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch(1)
        hint = QLabel("Pick a photo from your machine.")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        pick_btn = QPushButton("Choose photo…")
        pick_btn.setObjectName("primaryButton")
        pick_btn.clicked.connect(self._pick_file)
        layout.addWidget(pick_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        return page

    def _build_camera_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumHeight(360)
        layout.addWidget(self._video_widget, stretch=1)
        self._capture_btn = QPushButton("Take photo")
        self._capture_btn.setObjectName("primaryButton")
        self._capture_btn.clicked.connect(self._capture_photo)
        layout.addWidget(self._capture_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        return page

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose a photo",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.heic *.heif);;All files (*)",
        )
        if not path:
            return
        self._selected_path = self._persist_image(Path(path))
        self.accept()

    def _enter_camera_mode(self) -> None:
        if not QMediaDevices.videoInputs():
            return
        self._stack.setCurrentIndex(1)
        if self._camera is None:
            self._camera = QCamera(QMediaDevices.defaultVideoInput())
            self._capture_session = QMediaCaptureSession()
            self._capture_session.setCamera(self._camera)
            self._image_capture = QImageCapture()
            self._capture_session.setImageCapture(self._image_capture)
            self._capture_session.setVideoOutput(self._video_widget)
            self._image_capture.imageCaptured.connect(self._on_image_captured)
        self._camera.start()

    def _capture_photo(self) -> None:
        if self._image_capture is None:
            return
        self._pending_capture_path = self._uploads_dir / f"capture-{uuid.uuid4().hex}.jpg"
        self._image_capture.captureToFile(str(self._pending_capture_path))

    def _on_image_captured(self, _id: int, image: QImage) -> None:
        if self._pending_capture_path is None:
            return
        if image.isNull():
            self._pending_capture_path.unlink(missing_ok=True)
            self._pending_capture_path = None
            return
        if not image.save(str(self._pending_capture_path), "JPG"):
            self._pending_capture_path.unlink(missing_ok=True)
            self._pending_capture_path = None
            return
        self._selected_path = str(self._pending_capture_path)
        self._pending_capture_path = None
        QTimer.singleShot(0, self.accept)

    def _persist_image(self, source: Path) -> str:
        dest = self._uploads_dir / f"upload-{uuid.uuid4().hex}{source.suffix.lower() or '.jpg'}"
        shutil.copy2(source, dest)
        return str(dest)

    def done(self, result: int) -> None:
        if self._camera is not None:
            self._camera.stop()
        super().done(result)
