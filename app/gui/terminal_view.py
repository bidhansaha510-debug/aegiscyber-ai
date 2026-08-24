from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QComboBox, QPushButton, QLineEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.gui.theme import COLORS


class TerminalPage(QWidget):
    command_submitted = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("🖥 Terminal Output")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {COLORS['text_bright']};"
        )
        layout.addWidget(title)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Cascadia Code", 11))
        self._output.setStyleSheet(
            f"QPlainTextEdit {{ background-color: #0c0c0c; color: #cccccc; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; "
            f"padding: 12px; font-family: 'Cascadia Code', 'Consolas', monospace; }}"
        )
        layout.addWidget(self._output, 1)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self._backend_combo = QComboBox()
        self._backend_combo.addItems(["native", "wsl2", "docker"])
        self._backend_combo.setCurrentText("wsl2")
        self._backend_combo.setMinimumWidth(120)
        input_layout.addWidget(self._backend_combo)

        self._cmd_input = QLineEdit()
        self._cmd_input.setPlaceholderText("Enter command (goes through policy validation)...")
        self._cmd_input.setFont(QFont("Cascadia Code", 12))
        self._cmd_input.returnPressed.connect(self._on_submit)
        input_layout.addWidget(self._cmd_input, 1)

        self._run_btn = QPushButton("▶ Run")
        self._run_btn.setObjectName("primaryButton")
        self._run_btn.clicked.connect(self._on_submit)
        input_layout.addWidget(self._run_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._output.clear)
        input_layout.addWidget(clear_btn)

        layout.addLayout(input_layout)

    def _on_submit(self) -> None:
        cmd = self._cmd_input.text().strip()
        if cmd:
            backend = self._backend_combo.currentText()
            self.append_output(f"\n[{backend}] $ {cmd}\n", COLORS["accent_cyan"])
            self.command_submitted.emit(cmd, backend)
            self._cmd_input.clear()

    def append_output(self, text: str, color: str = "") -> None:
        self._output.appendPlainText(text)
        scrollbar = self._output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_error(self, text: str) -> None:
        self._output.appendPlainText(f"[ERROR] {text}")

    def set_running(self, running: bool) -> None:
        self._cmd_input.setEnabled(not running)
        self._run_btn.setEnabled(not running)
        self._run_btn.setText("⏳ Running..." if running else "▶ Run")
