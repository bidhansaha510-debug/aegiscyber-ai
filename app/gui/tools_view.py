from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from app.gui.theme import COLORS, RISK_COLORS, FONT_SANS, FONT_MONO
from app.stealth.opsec_engine import TOOL_NOISE_PROFILES
from app.mitre.attack_mapper import TOOL_TECHNIQUE_MAP


class _RiskPillWidget(QWidget):
    """Small rounded pill showing risk level with semantic color."""

    def __init__(self, risk: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)

        bg = RISK_COLORS.get(risk, COLORS["text_muted"])
        label = QLabel(risk.replace("_", " "))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"background-color: {bg}; color: #FFFFFF; "
            f"font-family: {FONT_SANS}; font-size: 10px; font-weight: 700; "
            f"padding: 2px 8px; border-radius: 4px;"
        )
        layout.addWidget(label)
        layout.addStretch()


class ToolsPage(QWidget):
    scan_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Tool Registry")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {COLORS['text_primary']}; "
            f"font-family: {FONT_SANS};"
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
        self._category_filter.setMinimumWidth(200)
        self._category_filter.currentIndexChanged.connect(self._filter_tools)
        filter_layout.addWidget(self._category_filter)

        scan_btn = QPushButton("Scan Tools")
        scan_btn.setObjectName("secondaryButton")
        scan_btn.clicked.connect(self.scan_requested.emit)
        filter_layout.addWidget(scan_btn)
        self._scan_btn = scan_btn

        layout.addLayout(filter_layout)

        self._table = QTableWidget()
        self._table.setColumnCount(9)
        self._table.setHorizontalHeaderLabels([
            "Tool", "Category", "Backend", "Risk Level", "OPSEC Score",
            "Status", "Success Rate", "MITRE ATT&CK", "Capabilities"
        ])

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)

        header.setMinimumSectionSize(80)
        self._table.setColumnWidth(0, 140)
        self._table.setColumnWidth(3, 110)
        self._table.setColumnWidth(4, 100)
        self._table.setColumnWidth(5, 100)
        self._table.setColumnWidth(6, 90)
        self._table.setColumnWidth(7, 140)

        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(False)
        self._table.setShowGrid(True)

        layout.addWidget(self._table, 1)

        self._status_label = QLabel(
            "No tools loaded — use Scan Tools to discover available tools."
        )
        self._status_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-family: {FONT_SANS}; font-size: 12px;"
        )
        layout.addWidget(self._status_label)

        self._all_tools: list[dict] = []

    def populate_tools(self, tools: list[Any]) -> None:
        dict_tools = []
        for t in tools:
            if isinstance(t, dict):
                dict_tools.append(t)
            else:
                dict_tools.append({
                    "name": getattr(t, "name", ""),
                    "categories": [getattr(t, "category", "")] if isinstance(getattr(t, "category", ""), str) else getattr(t, "category", []),
                    "backends": getattr(t, "execution_backend", ["native"]),
                    "risk_level": getattr(t, "danger_level", "LOW_RISK"),
                    "installed": getattr(t, "is_available", True),
                    "success_rate": 0.0,
                    "capabilities": getattr(t, "capabilities", []),
                })
        self.load_tools(dict_tools)

    def load_tools(self, tools: list[dict]) -> None:
        self._all_tools = tools

        categories = set()
        for tool in tools:
            for cat in tool.get("categories", []):
                if cat:
                    categories.add(cat)

        self._category_filter.clear()
        self._category_filter.addItem("All Categories", "")
        for cat in sorted(categories):
            self._category_filter.addItem(cat, cat)

        self._populate_table(tools)
        installed = sum(1 for t in tools if t.get("installed", False))
        if tools:
            self._status_label.setText(f"{installed} installed / {len(tools)} total tools")
        else:
            self._status_label.setText(
                "No tools loaded — use Scan Tools to discover available tools."
            )

    def _populate_table(self, tools: list[dict]) -> None:
        self._table.setRowCount(len(tools))
        for row, tool in enumerate(tools):
            name_item = QTableWidgetItem(tool.get("name", ""))
            name_item.setFont(self._mono_font())
            self._table.setItem(row, 0, name_item)

            cat_text = ", ".join(tool.get("categories", []))
            cat_item = QTableWidgetItem(cat_text)
            cat_item.setToolTip(cat_text)
            self._table.setItem(row, 1, cat_item)

            backend_text = ", ".join(tool.get("backends", []))
            backend_item = QTableWidgetItem(backend_text)
            backend_item.setToolTip(backend_text)
            self._table.setItem(row, 2, backend_item)

            risk = tool.get("risk_level", "LOW_RISK")
            pill = _RiskPillWidget(risk)
            self._table.setCellWidget(row, 3, pill)

            tool_name = tool.get("name", "").lower()
            noise_profile = TOOL_NOISE_PROFILES.get(tool_name)
            if noise_profile:
                opsec_val = noise_profile["detection_weight"]
                opsec_item = QTableWidgetItem(f"{opsec_val}/100")
                opsec_item.setFont(self._mono_font())
                opsec_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if opsec_val < 30:
                    opsec_item.setForeground(QColor("#4caf50"))
                elif opsec_val < 60:
                    opsec_item.setForeground(QColor("#ff9800"))
                else:
                    opsec_item.setForeground(QColor("#f44336"))
                opsec_item.setToolTip(
                    f"Traffic: {noise_profile['traffic_volume']}, "
                    f"Signatures: {noise_profile['signature_count']}, "
                    f"Log footprint: {noise_profile['log_footprint']}"
                )
            else:
                opsec_item = QTableWidgetItem("—")
                opsec_item.setFont(self._mono_font())
                opsec_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 4, opsec_item)

            installed = tool.get("installed", False)
            status_text = "Installed" if installed else "Not Found"
            status_item = QTableWidgetItem(status_text)
            status_color = COLORS["state_clear"] if installed else COLORS["text_muted"]
            status_item.setForeground(QColor(status_color))
            self._table.setItem(row, 5, status_item)

            rate = tool.get("success_rate", 0)
            rate_item = QTableWidgetItem(f"{rate:.0%}" if rate else "—")
            rate_item.setFont(self._mono_font())
            rate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 6, rate_item)

            techniques = TOOL_TECHNIQUE_MAP.get(tool_name, [])
            if techniques:
                tech_ids = ", ".join(t["technique_id"] for t in techniques[:3])
                tech_names = "\n".join(
                    f"{t['technique_id']}: {t['technique_name']}" for t in techniques
                )
                mitre_item = QTableWidgetItem(tech_ids)
                mitre_item.setToolTip(tech_names)
                mitre_item.setForeground(QColor("#66b1ff"))
            else:
                mitre_item = QTableWidgetItem("—")
            mitre_item.setFont(self._mono_font())
            self._table.setItem(row, 7, mitre_item)

            caps = ", ".join(tool.get("capabilities", [])[:3])
            caps_item = QTableWidgetItem(caps)
            caps_item.setToolTip(", ".join(tool.get("capabilities", [])))
            self._table.setItem(row, 8, caps_item)

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

    @staticmethod
    def _mono_font():
        from PySide6.QtGui import QFont
        return QFont("JetBrains Mono", 11)
