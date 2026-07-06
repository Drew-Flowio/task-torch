"""GPU-light micro-interactions for the field UI."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ui.touch import tokens as t


class BreathingRingWidget(QWidget):
    """Soft idle breathing ring on the logo area."""

    def __init__(self, size: int = 36, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._phase = 0
        self._active = True
        self._timer = QTimer(self)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_breathing(self, active: bool) -> None:
        self._active = active
        if active and not self._timer.isActive():
            self._timer.start()
        elif not active:
            self._timer.stop()
            self.update()

    def _tick(self) -> None:
        if self._active:
            self._phase = (self._phase + 1) % 40
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._active:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        outer = self.width() * 0.42
        alpha = 40 + int(25 * (1 + (self._phase / 20.0 - 1) ** 2))
        pen = QPen(QColor(t.ACCENT))
        pen.setColor(QColor(t.ACCENT))
        c = pen.color()
        c.setAlpha(alpha)
        pen.setColor(c)
        pen.setWidthF(2.0)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(int(cx - outer), int(cy - outer), int(outer * 2), int(outer * 2))
        p.end()


class WaveformBar(QWidget):
    """Simple speaking waveform — 5 bars, timer-driven."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(20)
        self.setMinimumWidth(48)
        self._levels = [0.2, 0.35, 0.5, 0.35, 0.2]
        self._step = 0
        self._active = False
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._tick)

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self._timer.start()
            self.show()
        else:
            self._timer.stop()
            self.hide()

    def _tick(self) -> None:
        self._step += 1
        base = [0.15, 0.25, 0.4, 0.25, 0.15]
        self._levels = [
            min(1.0, base[i] + 0.35 * abs(((self._step + i) % 6) - 3) / 3)
            for i in range(5)
        ]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._active:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bar_w = 4
        gap = 3
        x = 4
        for level in self._levels:
            h = max(3, int(level * (self.height() - 4)))
            y = (self.height() - h) // 2
            p.fillRect(x, y, bar_w, h, QColor(t.ACCENT))
            x += bar_w + gap
        p.end()


class ScanPulseWidget(QWidget):
    """Lightweight thinking / scanning indicator."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(56, 14)
        self._dots = [0, 0, 0]
        self._step = 0
        self._active = False
        self._timer = QTimer(self)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._tick)

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self._timer.start()
            self.show()
        else:
            self._timer.stop()
            self.hide()

    def _tick(self) -> None:
        self._step = (self._step + 1) % 3
        self._dots = [1 if i == self._step else 0 for i in range(3)]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._active:
            return
        p = QPainter(self)
        x = 8
        for on in self._dots:
            color = QColor(t.ACCENT if on else t.BORDER)
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(x, 3, 8, 8)
            x += 16
        p.end()
