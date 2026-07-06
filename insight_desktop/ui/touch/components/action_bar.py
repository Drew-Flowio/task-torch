"""Bottom action bar — five equal hardware-style control cards."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.touch import tokens as t
from ui.touch.mic_button import MicButton


class ActionCard(QFrame):
    """Single touch target card in the bottom bar."""

    clicked = Signal()

    def __init__(
        self,
        title: str,
        icon: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("actionCard")
        self.setMinimumHeight(t.MIN_TOUCH + 20)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 8, 6, 8)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon = QLabel(icon)
        self._icon.setObjectName("actionCardIcon")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel(title)
        self._title.setObjectName("actionCardTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay.addWidget(self._icon)
        lay.addWidget(self._title)

        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("actionCardSubtitle")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setWordWrap(True)
        if subtitle:
            lay.addWidget(self._subtitle)
        else:
            self._subtitle.hide()

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)
        self._subtitle.setVisible(bool(text))

    def set_active(self, active: bool) -> None:
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self.isEnabled() and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class MicActionCard(QFrame):
    """Mic card with tap / hold gestures preserved from MicButton."""

    tapped = Signal()
    long_pressed = Signal()
    end_conversation = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("actionCard")
        self.setProperty("mic", True)
        self.setMinimumHeight(t.MIN_TOUCH + 20)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 6, 4, 6)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._mic = MicButton()
        self._mic.setObjectName("micActionBtn")
        self._mic.setFixedSize(t.MIN_TOUCH, t.MIN_TOUCH)
        self._mic.tapped.connect(self.tapped.emit)
        self._mic.long_pressed.connect(self.long_pressed.emit)

        self._title = QLabel("MIC")
        self._title.setObjectName("actionCardTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._hint = QLabel("Tap · Hold")
        self._hint.setObjectName("actionCardSubtitle")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._end = QPushButton("End")
        self._end.setObjectName("micEndBtn")
        self._end.hide()
        self._end.clicked.connect(self.end_conversation.emit)

        lay.addWidget(self._mic, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._title)
        lay.addWidget(self._hint)
        lay.addWidget(self._end)

    @property
    def mic_button(self) -> MicButton:
        return self._mic

    def set_conversation_mode(self, active: bool) -> None:
        self._mic.set_conversation_mode(active)
        self.setProperty("active", active)
        self._end.setVisible(active)
        self._hint.setText("Conversation" if active else "Tap · Hold")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_one_shot_recording(self, active: bool) -> None:
        self._mic.set_one_shot_recording(active)
        if not self.property("active"):
            self._hint.setText("Stop" if active else "Tap · Hold")

    def set_listening_pulse(self, active: bool) -> None:
        self._mic.set_listening_pulse(active)


class BottomActionBar(QWidget):
    capture_clicked = Signal()
    expert_pack_clicked = Signal()
    memory_clicked = Signal()
    tools_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("bottomActionBar")
        self.setFixedHeight(t.MIN_TOUCH + 28)

        grid = QGridLayout(self)
        grid.setContentsMargins(0, t.SPACE_XS, 0, 0)
        grid.setSpacing(t.SPACE_SM)

        self.mic = MicActionCard()
        self.capture = ActionCard("CAPTURE", "◎", "Quick capture")
        self.expert = ActionCard("EXPERT", "◆", "General")
        self.memory = ActionCard("MEMORY", "◉", "OFF")
        self.tools = ActionCard("TOOLS", "☰", "More")

        self.capture.clicked.connect(self.capture_clicked.emit)
        self.expert.clicked.connect(self.expert_pack_clicked.emit)
        self.memory.clicked.connect(self.memory_clicked.emit)
        self.tools.clicked.connect(self.tools_clicked.emit)

        for i, card in enumerate((self.mic, self.capture, self.expert, self.memory, self.tools)):
            grid.addWidget(card, 0, i)

    def set_memory_status(self, on: bool, count: int = 0) -> None:
        label = "ON" if on else "OFF"
        detail = f"{count} fact{'s' if count != 1 else ''}" if on else "No facts"
        self.memory.set_subtitle(f"{label} · {detail}")

    def set_expert_pack(self, name: str) -> None:
        self.expert.set_subtitle(name)

    def set_capture_enabled(self, enabled: bool) -> None:
        self.capture.setEnabled(enabled)

    def set_mic_enabled(self, enabled: bool) -> None:
        self.mic.setEnabled(enabled)
        self.mic.mic_button.setEnabled(enabled)
