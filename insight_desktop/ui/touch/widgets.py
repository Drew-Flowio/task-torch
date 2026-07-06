"""AI response panel and shared touch widgets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from ui.touch import tokens as t


class AiResponsePanel(QScrollArea):
    """30% side panel — structured AI output, compact, auto-sizing sections."""

    _SECTION_ORDER = (
        ("Direct Answer", "direct"),
        ("What I Noticed", "noticed"),
        ("What To Do Next", "next"),
        ("Confidence", "confidence"),
        ("Source", "source"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("aiPanel")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._body = QWidget()
        self.setWidget(self._body)
        self._layout = QVBoxLayout(self._body)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(t.SPACE_SM)

        self._title_row = QLabel("AI RESPONSE")
        self._title_row.setObjectName("aiPanelTitle")
        self._layout.addWidget(self._title_row)

        self._mode_label = QLabel("")
        self._mode_label.setObjectName("aiModeLabel")
        self._mode_label.hide()
        self._layout.addWidget(self._mode_label)

        self._sections: list[QFrame] = []
        self._show_idle()

    def set_voice_mode_label(self, text: str | None) -> None:
        if text:
            self._mode_label.setText(text)
            self._mode_label.show()
        else:
            self._mode_label.hide()

    def clear_answer(self) -> None:
        self._clear_sections()
        self._show_idle()

    def set_answer(
        self,
        text: str,
        image_caption: str | None = None,
        source: str = "On-device model",
    ) -> None:
        self._clear_sections()
        parts: dict[str, str] = {}

        if text.strip():
            parts["direct"] = text.strip()
        if image_caption:
            parts["noticed"] = image_caption.strip()

        next_step = _extract_section(text, ("next", "do this", "try", "start by"))
        if next_step:
            parts["next"] = next_step

        if image_caption or text.strip():
            parts["confidence"] = (
                "Based on what I can see and hear on this device."
                if image_caption
                else "Based on local knowledge and your question."
            )
            parts["source"] = source

        if not parts:
            self._show_idle()
            return

        for heading, key in self._SECTION_ORDER:
            body = parts.get(key)
            if body:
                self._add_section(heading, body)

    def set_error(self, message: str) -> None:
        self._clear_sections()
        self._add_section("Error", message, accent=t.ERROR)

    def _show_idle(self) -> None:
        label = QLabel("Awaiting input")
        label.setObjectName("aiIdleLabel")
        label.setWordWrap(True)
        frame = QFrame()
        frame.setObjectName("aiSectionCard")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.addWidget(label)
        self._sections.append(frame)
        self._layout.addWidget(frame)

    def _clear_sections(self) -> None:
        while self._layout.count() > 2:
            item = self._layout.takeAt(2)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for frame in self._sections:
            frame.deleteLater()
        self._sections.clear()

    def _add_section(self, title: str, body: str, accent: str = t.ACCENT) -> None:
        frame = QFrame()
        frame.setObjectName("aiSectionCard")
        col = QVBoxLayout(frame)
        col.setContentsMargins(12, 10, 12, 10)
        col.setSpacing(4)
        heading = QLabel(title.upper())
        heading.setObjectName("aiSectionTitle")
        heading.setStyleSheet(f"color:{accent};")
        content = QLabel(body)
        content.setObjectName("aiSectionBody")
        content.setWordWrap(True)
        content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        col.addWidget(heading)
        col.addWidget(content)
        self._sections.append(frame)
        self._layout.addWidget(frame)


def _extract_section(text: str, keywords: tuple[str, ...]) -> str | None:
    for sentence in text.replace("\n", " ").split(". "):
        s = sentence.strip()
        if not s:
            continue
        if any(k in s.lower() for k in keywords) and len(s) > 12:
            return s if s.endswith(".") else f"{s}."
    return None
