"""One-tap Expert Pack picker sheet."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout

from ui.touch.expert_packs import ExpertPack, ExpertPackStore


class ExpertPackSheet(QDialog):
    def __init__(self, store: ExpertPackStore, parent=None) -> None:
        super().__init__(parent)
        self._store = store
        self.setObjectName("touchSheet")
        self.setWindowTitle("Expert Pack")
        self.resize(440, 420)

        layout = QVBoxLayout(self)
        title = QLabel("Select Expert Pack")
        title.setObjectName("sheetTitle")
        layout.addWidget(title)

        hint = QLabel("Packs shape how the AI reasons. All processing stays on-device.")
        hint.setObjectName("sheetHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._list = QListWidget()
        self._list.setObjectName("packList")
        for pack in store.all_packs():
            item = QListWidgetItem(f"{pack.name}  ·  v{pack.version}\n{pack.trust}")
            item.setData(Qt.ItemDataRole.UserRole, pack.id)
            if pack.id == store.active.id:
                item.setSelected(True)
            self._list.addItem(item)
        self._list.itemDoubleClicked.connect(self._accept_selection)
        layout.addWidget(self._list, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondaryButton")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def _accept_selection(self, item: QListWidgetItem) -> None:
        self._store.set_active(item.data(Qt.ItemDataRole.UserRole))
        self.accept()

    @property
    def selected_pack(self) -> ExpertPack:
        return self._store.active
