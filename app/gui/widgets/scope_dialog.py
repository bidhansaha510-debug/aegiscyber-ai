from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QListWidget, QListWidgetItem, QWidget,
)
from PySide6.QtCore import Qt, Signal

from app.gui.theme import COLORS
from app.security.authorization import ScopeType


class ScopeDialog(QDialog):
    scope_updated = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure Target Scope")
        self.setMinimumSize(500, 400)
        self.setStyleSheet(f"QDialog {{ background-color: {COLORS['bg_secondary']}; }}")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Target Scope Configuration")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLORS['accent_cyan']}; "
            f"padding: 8px 0;"
        )
        layout.addWidget(title)

        desc = QLabel(
            "Define the authorized targets for this session. "
            "Only targets within this scope will be allowed."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; padding-bottom: 8px;")
        layout.addWidget(desc)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self._type_combo = QComboBox()
        for scope_type in ScopeType:
            self._type_combo.addItem(scope_type.value, scope_type)
        self._type_combo.setMinimumWidth(150)
        input_layout.addWidget(self._type_combo)

        self._value_input = QLineEdit()
        self._value_input.setPlaceholderText("e.g., 192.168.1.0/24 or example.com")
        input_layout.addWidget(self._value_input, 1)

        add_btn = QPushButton("+ Add")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._add_entry)
        input_layout.addWidget(add_btn)

        layout.addLayout(input_layout)

        self._scope_list = QListWidget()
        self._scope_list.setMinimumHeight(150)
        layout.addWidget(self._scope_list, 1)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_entry)
        layout.addWidget(remove_btn)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        confirm_btn = QPushButton("Confirm Scope")
        confirm_btn.setObjectName("primaryButton")
        confirm_btn.setMinimumWidth(150)
        confirm_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(confirm_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        self._entries: list[dict] = []

    def _add_entry(self) -> None:
        value = self._value_input.text().strip()
        if not value:
            return
        scope_type = self._type_combo.currentData()
        entry = {"type": scope_type.value, "value": value}
        self._entries.append(entry)
        self._scope_list.addItem(f"[{scope_type.value}] {value}")
        self._value_input.clear()

    def _remove_entry(self) -> None:
        row = self._scope_list.currentRow()
        if row >= 0:
            self._scope_list.takeItem(row)
            self._entries.pop(row)

    def _confirm(self) -> None:
        if self._entries:
            self.scope_updated.emit(self._entries)
            self.accept()

    def set_entries(self, entries: list[dict]) -> None:
        self._entries = entries
        self._scope_list.clear()
        for entry in entries:
            self._scope_list.addItem(f"[{entry['type']}] {entry['value']}")
