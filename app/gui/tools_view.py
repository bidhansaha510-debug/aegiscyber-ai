from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt

from app.gui.theme import COLORS, RISK_COLORS


class ToolsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Tool Registry")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {COLORS['text_bright']};"
        )
        layout.addWidget(title)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search tools...")
        self._search_input.textChanged.connect(self._filter_tools)
        filter_layout.addWidget(self._search_input, 1)

        self._category_filter = QComboBox()
        self._category_filter.addItem("All Categories", "")
        self._category_filter.setMinimumWidth(180)
        self._category_filter.currentIndexChanged.connect(self._filter_tools)
        filter_layout.addWidget(self._category_filter)

        scan_btn = QPushButton("Scan Tools")
        scan_btn.setObjectName("primaryButton")
        filter_layout.addWidget(scan_btn)
        self._scan_btn = scan_btn

        layout.addLayout(filter_layout)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Tool", "Category", "Backend", "Risk Level", "Status", "Success Rate", "Capabilities"
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            f"QTableWidget {{ alternate-background-color: {COLORS['bg_card']}; }}"
        )
        layout.addWidget(self._table, 1)

        self._status_label = QLabel("No tools loaded")
        self._status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(self._status_label)

        self._all_tools: list[dict] = []

    def load_tools(self, tools: list[dict]) -> None:
        self._all_tools = tools

        categories = set()
        for tool in tools:
            for cat in tool.get("categories", []):
                categories.add(cat)

        self._category_filter.clear()
        self._category_filter.addItem("All Categories", "")
        for cat in sorted(categories):
            self._category_filter.addItem(cat, cat)

        self._populate_table(tools)
        installed = sum(1 for t in tools if t.get("installed", False))
        self._status_label.setText(f"{installed} installed / {len(tools)} total tools")

    def _populate_table(self, tools: list[dict]) -> None:
        self._table.setRowCount(len(tools))
        for row, tool in enumerate(tools):
            self._table.setItem(row, 0, QTableWidgetItem(tool.get("name", "")))
            self._table.setItem(row, 1, QTableWidgetItem(", ".join(tool.get("categories", []))))
            self._table.setItem(row, 2, QTableWidgetItem(", ".join(tool.get("backends", []))))

            risk = tool.get("risk_level", "LOW_RISK")
            risk_item = QTableWidgetItem(risk)
            risk_color = RISK_COLORS.get(risk, COLORS["text_primary"])
            risk_item.setForeground(Qt.GlobalColor.white)
            self._table.setItem(row, 3, risk_item)

            status = "[+] Installed" if tool.get("installed") else "[-] Not Found"
            status_item = QTableWidgetItem(status)
            self._table.setItem(row, 4, status_item)

            rate = tool.get("success_rate", 0)
            self._table.setItem(row, 5, QTableWidgetItem(f"{rate:.0%}" if rate else "--"))

            caps = ", ".join(tool.get("capabilities", [])[:3])
            self._table.setItem(row, 6, QTableWidgetItem(caps))

    def _filter_tools(self) -> None:
        search = self._search_input.text().lower()
        category = self._category_filter.currentData()

        filtered = []
        for tool in self._all_tools:
            if search and search not in tool.get("name", "").lower() and search not in str(tool.get("capabilities", [])).lower():
                continue
            if category and category not in tool.get("categories", []):
                continue
            filtered.append(tool)

        self._populate_table(filtered)
