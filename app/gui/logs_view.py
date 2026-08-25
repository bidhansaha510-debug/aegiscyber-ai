from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QComboBox, QPushButton, QLineEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.gui.theme import COLORS, FONT_SANS, FONT_MONO


class LogsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header area ──
        header_area = QWidget()
        header_layout = QVBoxLayout(header_area)
        header_layout.setContentsMargins(24, 24, 24, 16)
        header_layout.setSpacing(16)

        title = QLabel("Audit Logs")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {COLORS['text_primary']}; "
            f"font-family: {FONT_SANS};"
        )
        header_layout.addWidget(title)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Filter logs...")
        filter_layout.addWidget(self._search_input, 1)

        self._level_filter = QComboBox()
        self._level_filter.addItems(["All Levels", "INFO", "WARNING", "ERROR", "SECURITY", "AUDIT"])
        self._level_filter.setMinimumWidth(140)
        filter_layout.addWidget(self._level_filter)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self._clear_logs)
        filter_layout.addWidget(clear_btn)

        export_btn = QPushButton("Export")
        export_btn.setObjectName("secondaryButton")
        filter_layout.addWidget(export_btn)

        header_layout.addLayout(filter_layout)
        layout.addWidget(header_area)

        # ── Log Output (console style — 0 radius) ──
        self._log_output = QPlainTextEdit()
        self._log_output.setReadOnly(True)
        self._log_output.setFont(QFont("JetBrains Mono", 10))
        self._log_output.setMaximumBlockCount(5000)
        self._log_output.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {COLORS['bg_void']}; "
            f"color: {COLORS['text_primary']}; "
            f"border: none; border-top: 1px solid {COLORS['border_hairline']}; "
            f"border-radius: 0px; padding: 8px 16px; "
            f"font-family: {FONT_MONO}; font-size: 11px; }}"
        )
        self._log_output.setPlaceholderText(
            "No actions logged yet — commands you run will appear here."
        )
        layout.addWidget(self._log_output, 1)

        # ── Footer ──
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 4, 24, 8)

        self._count_label = QLabel(
            "No actions logged yet — commands you run will appear here."
        )
        self._count_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-family: {FONT_MONO}; "
            f"font-size: 11px;"
        )
        footer_layout.addWidget(self._count_label)
        footer_layout.addStretch()

        layout.addWidget(footer)

        self._log_count = 0

    def append_log(self, message: str) -> None:
        self._log_output.appendPlainText(message)
        self._log_count += 1
        self._count_label.setText(f"{self._log_count} log entries")

    def _clear_logs(self) -> None:
        self._log_output.clear()
        self._log_count = 0
        self._count_label.setText(
            "No actions logged yet — commands you run will appear here."
        )
