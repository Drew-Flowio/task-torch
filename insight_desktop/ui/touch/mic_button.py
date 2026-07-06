"""Microphone button with tap (one-shot) and long-press (conversation) gestures."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QPushButton


class MicButton(QPushButton):
    """Tap = one-shot. Hold >= threshold = conversation mode entry."""

    tapped = Signal()
    long_pressed = Signal()

    LONG_PRESS_MS = 450
    _ICON_READY = "🎙"
    _ICON_STOP = "■"

    def __init__(self, parent=None) -> None:
        super().__init__(self._ICON_READY, parent)
        self.setObjectName("micActionBtn")
        self._long_press_fired = False
        self._press_timer = QTimer(self)
        self._press_timer.setSingleShot(True)
        self._press_timer.setInterval(self.LONG_PRESS_MS)
        self._press_timer.timeout.connect(self._on_long_press)
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(800)
        self._pulse_timer.timeout.connect(self._toggle_pulse)
        self._pulse_on = False

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self.isEnabled():
            return
        self._long_press_fired = False
        self._press_timer.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._press_timer.stop()
        if self.isEnabled() and not self._long_press_fired:
            self.tapped.emit()
        super().mouseReleaseEvent(event)

    def _on_long_press(self) -> None:
        self._long_press_fired = True
        self.long_pressed.emit()

    def set_conversation_mode(self, active: bool) -> None:
        self.setProperty("conversation", active)
        if active:
            self.setText(self._ICON_READY)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_one_shot_recording(self, active: bool) -> None:
        self.setText(self._ICON_STOP if active else self._ICON_READY)
        self.setProperty("recording", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_listening_pulse(self, active: bool) -> None:
        if active:
            self._pulse_on = False
            self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
            self.setProperty("pulsing", False)
            self.style().unpolish(self)
            self.style().polish(self)

    def _toggle_pulse(self) -> None:
        self._pulse_on = not self._pulse_on
        self.setProperty("pulsing", self._pulse_on)
        self.style().unpolish(self)
        self.style().polish(self)
