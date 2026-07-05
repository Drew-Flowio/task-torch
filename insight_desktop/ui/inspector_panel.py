"""The side inspector: personality, memory, and debug views."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from engine.interface import InsightEngine
from ui import theme


class InspectorPanel(QWidget):
    session_reset = Signal()

    def __init__(self, engine: InsightEngine) -> None:
        super().__init__()
        self._engine = engine
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("Inspector")
        header.setStyleSheet(
            f"font-size:13px; font-weight:600; color:{theme.INK}; "
            f"padding:16px 18px 12px 18px; background:{theme.SURFACE}; "
            f"border-bottom:1px solid {theme.BORDER};"
        )
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        layout.addWidget(tabs, stretch=1)

        tabs.addTab(self._build_personality_tab(), "Personality")
        tabs.addTab(self._build_memory_tab(), "Memory")
        tabs.addTab(self._build_debug_tab(), "Debug")

    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def _build_personality_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(self._section("System prompt"))
        hint = QLabel("Edit below, then save as a new version. Double-click a past version to activate it.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{theme.MUTED}; font-size:11px; margin-bottom:2px;")
        layout.addWidget(hint)

        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setStyleSheet(f"font-family:{theme.FONT_MONO}; font-size:12px;")
        self._prompt_edit.setMinimumHeight(180)
        layout.addWidget(self._prompt_edit, stretch=3)

        save_row = QHBoxLayout()
        save_row.setSpacing(8)
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("Version label (optional)")
        save_row.addWidget(self._label_edit)
        save_btn = QPushButton("Save version")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._on_save_prompt)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)

        layout.addWidget(self._section("Version history"))
        self._version_list = QListWidget()
        self._version_list.itemDoubleClicked.connect(self._on_activate_version)
        layout.addWidget(self._version_list, stretch=2)

        return widget

    def _build_memory_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(self._section("Current session"))
        self._state_label = QLabel()
        self._state_label.setObjectName("cardLabel")
        self._state_label.setWordWrap(True)
        layout.addWidget(self._state_label)

        layout.addWidget(self._section("Long-term memory"))
        mem_hint = QLabel("Facts Insight remembers across conversation resets.")
        mem_hint.setStyleSheet(f"color:{theme.MUTED}; font-size:11px;")
        layout.addWidget(mem_hint)

        self._facts_list = QListWidget()
        self._facts_list.setMinimumHeight(100)
        layout.addWidget(self._facts_list, stretch=2)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self._fact_edit = QLineEdit()
        self._fact_edit.setPlaceholderText('e.g. "2018 Subaru Outback"')
        self._fact_edit.returnPressed.connect(self._on_add_fact)
        add_row.addWidget(self._fact_edit)
        add_btn = QPushButton("Add")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._on_add_fact)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        remove_btn = QPushButton("Remove selected")
        remove_btn.setObjectName("ghostButton")
        remove_btn.clicked.connect(self._on_remove_fact)
        layout.addWidget(remove_btn)

        layout.addSpacing(8)
        layout.addWidget(self._section("Reset"))

        reset_session_btn = QPushButton("New conversation")
        reset_session_btn.clicked.connect(lambda: self._on_reset("session"))
        layout.addWidget(reset_session_btn)

        reset_all_btn = QPushButton("Full reset (conversation + memory)")
        reset_all_btn.setObjectName("dangerButton")
        reset_all_btn.clicked.connect(lambda: self._on_reset("all"))
        layout.addWidget(reset_all_btn)

        layout.addStretch(1)
        return widget

    def _build_debug_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(self._section("Last prompt sent to the LLM"))
        debug_hint = QLabel("See exactly what context produced the most recent reply.")
        debug_hint.setStyleSheet(f"color:{theme.MUTED}; font-size:11px;")
        layout.addWidget(debug_hint)

        self._debug_view = QPlainTextEdit()
        self._debug_view.setReadOnly(True)
        self._debug_view.setStyleSheet(f"font-family:{theme.FONT_MONO}; font-size:11px;")
        self._debug_view.setPlaceholderText("Send a message to populate this view.")
        layout.addWidget(self._debug_view, stretch=1)

        self._latency_label = QLabel("No response yet.")
        self._latency_label.setStyleSheet(f"color:{theme.MUTED}; font-size:12px; padding:4px 0;")
        layout.addWidget(self._latency_label)

        return widget

    def _on_save_prompt(self) -> None:
        text = self._prompt_edit.toPlainText()
        label = self._label_edit.text().strip() or None
        self._engine.update_prompt(text, label=label)
        self._label_edit.clear()
        self.refresh()

    def _on_activate_version(self, item: QListWidgetItem) -> None:
        self._engine.activate_prompt_version(item.data(Qt.ItemDataRole.UserRole))
        self.refresh()

    def _on_add_fact(self) -> None:
        text = self._fact_edit.text().strip()
        if text:
            self._engine.add_memory_fact(text)
            self._fact_edit.clear()
            self.refresh()

    def _on_remove_fact(self) -> None:
        item = self._facts_list.currentItem()
        if item is not None:
            self._engine.remove_memory_fact(item.data(Qt.ItemDataRole.UserRole))
            self.refresh()

    def _on_reset(self, scope: str) -> None:
        if scope == "all":
            confirm = QMessageBox.question(
                self,
                "Full reset",
                "This clears the conversation and all long-term memory facts.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        self._engine.reset_memory(scope=scope)
        self.refresh()
        self.session_reset.emit()

    def show_turn_debug(self, debug_text: str, latency_ms: int, cancelled: bool) -> None:
        self._debug_view.setPlainText(debug_text)
        status = "cancelled" if cancelled else "completed"
        self._latency_label.setText(f"Last turn {status} · {latency_ms:,} ms")

    def refresh(self) -> None:
        state = self._engine.get_session_state()
        self._state_label.setText(
            f"Session {state.session_id[:8]}…\n"
            f"{state.session_summary}\n"
            f"Active prompt: {state.active_prompt_label or 'initial'}\n"
            f"Memory facts: {state.memory_fact_count}"
        )

        current_prompt = self._engine.get_system_prompt()
        if not self._prompt_edit.hasFocus() and self._prompt_edit.toPlainText() != current_prompt:
            self._prompt_edit.setPlainText(current_prompt)

        self._version_list.clear()
        for version in self._engine.get_prompt_history():
            label = version.label or "initial"
            prefix = "● " if version.is_active else "  "
            item = QListWidgetItem(f"{prefix}{label}")
            item.setToolTip(version.created_at)
            item.setData(Qt.ItemDataRole.UserRole, version.id)
            if version.is_active:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self._version_list.addItem(item)

        self._facts_list.clear()
        for fact in self._engine.list_memory_facts():
            item = QListWidgetItem(fact.text)
            item.setData(Qt.ItemDataRole.UserRole, fact.id)
            self._facts_list.addItem(item)
