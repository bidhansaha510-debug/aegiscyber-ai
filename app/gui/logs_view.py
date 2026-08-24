from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QComboBox, QPushButton, QLineEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.gui.theme import COLORS


class LogsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Audit Logs")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {COLORS['text_bright']};"
        )
        layout.addWidget(title)

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
        clear_btn.clicked.connect(self._clear_logs)
        filter_layout.addWidget(clear_btn)

        export_btn = QPushButton("Export")
        filter_layout.addWidget(export_btn)

        layout.addLayout(filter_layout)

        self._log_output = QPlainTextEdit()
        self._log_output.setReadOnly(True)
        self._log_output.setFont(QFont("Cascadia Code", 10))
        self._log_output.setMaximumBlockCount(5000)
        self._log_output.setStyleSheet(
            f"QPlainTextEdit {{ background-color: #0c0c0c; color: #b0b0b0; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; "
            f"padding: 8px; font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 11px; }}"
        )
        layout.addWidget(self._log_output, 1)

        self._count_label = QLabel("0 log entries")
        self._count_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self._count_label)

        self._log_count = 0

    def append_log(self, message: str) -> None:
        self._log_output.appendPlainText(message)
        self._log_count += 1
        self._count_label.setText(f"{self._log_count} log entries")

    def _clear_logs(self) -> None:
        self._log_output.clear()
        self._log_count = 0
        self._count_label.setText("0 log entries")
