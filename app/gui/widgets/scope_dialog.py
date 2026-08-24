from __future__ import annotations

from typing import Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QListWidget, QListWidgetItem, QWidget,
)
from PySide6.QtCore import Qt, Signal

from app.gui.theme import COLORS
from app.security.authorization import ScopeType


class ScopeDialog(QDialog):
    scope_updated = Signal(list)

    def __init__(self, auth_manager: Any = None, parent: QWidget | None = None) -> None:
        if isinstance(auth_manager, QWidget) and parent is None:
            parent = auth_manager
            auth_manager = None
        super().__init__(parent)
        self._auth_manager = auth_manager
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
            val = scope_type.value if hasattr(scope_type, "value") else str(scope_type)
            self._type_combo.addItem(val, val)
        self._type_combo.setMinimumWidth(150)
        input_layout.addWidget(self._type_combo)

        self._value_input = QLineEdit()
        self._value_input.setPlaceholderText("e.g., 192.168.1.0/24 or example.com")
        self._value_input.returnPressed.connect(self._add_entry)
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

        if self._auth_manager and hasattr(self._auth_manager, "current_scope") and self._auth_manager.current_scope:
            for entry in self._auth_manager.current_scope.entries:
                st_val = entry.scope_type.value if hasattr(entry.scope_type, "value") else str(entry.scope_type)
                self._entries.append({"type": st_val, "value": entry.value})
                self._scope_list.addItem(f"[{st_val}] {entry.value}")

    def _add_entry(self) -> None:
        value = self._value_input.text().strip()
        if not value:
            return
        raw_type = self._type_combo.currentData() or self._type_combo.currentText()
        scope_type_str = raw_type.value if hasattr(raw_type, "value") else str(raw_type)
        entry = {"type": scope_type_str, "value": value}
        self._entries.append(entry)
        self._scope_list.addItem(f"[{scope_type_str}] {value}")
        self._value_input.clear()

    def _remove_entry(self) -> None:
        row = self._scope_list.currentRow()
        if row >= 0:
            self._scope_list.takeItem(row)
            self._entries.pop(row)

    def _confirm(self) -> None:
        if self._auth_manager and self._entries:
            scope = self._auth_manager.current_scope
            scope.entries.clear()
            for e in self._entries:
                st_val = e.get("type", "domain")
                st = next((s for s in ScopeType if s.value == st_val), ScopeType.DOMAIN)
                scope.add_entry(st, e.get("value", ""))
            try:
                scope.confirm()
                scope.activate()
            except Exception:
                pass
        self.scope_updated.emit(self._entries)
        self.accept()

    def set_entries(self, entries: list[dict]) -> None:
        self._entries = list(entries)
        self._scope_list.clear()
        for entry in self._entries:
            t = entry.get("type", "domain")
            v = entry.get("value", "")
            self._scope_list.addItem(f"[{t}] {v}")
