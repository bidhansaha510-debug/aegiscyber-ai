from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QComboBox, QPushButton, QLineEdit, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.gui.theme import COLORS, FONT_MONO, FONT_SANS


class TerminalPage(QWidget):
    command_submitted = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Console Chrome Title Bar ──
        title_bar = QFrame()
        title_bar.setFixedHeight(36)
        title_bar.setStyleSheet(
            f"background-color: {COLORS['bg_surface_raised']}; "
            f"border-bottom: 1px solid {COLORS['border_hairline']};"
        )
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(16, 0, 16, 0)
        tb_layout.setSpacing(8)

        self._title_label = QLabel("wsl2 — kali")
        self._title_label.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 12px; font-weight: 600; "
            f"color: {COLORS['text_muted']}; background: transparent;"
        )
        tb_layout.addWidget(self._title_label)
        tb_layout.addStretch()

        layout.addWidget(title_bar)

        # ── Output Area (0 radius — reads as console) ──
        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont("JetBrains Mono", 11))
        self._output.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {COLORS['bg_void']}; "
            f"color: {COLORS['text_primary']}; "
            f"border: none; border-radius: 0px; "
            f"padding: 16px; font-family: {FONT_MONO}; font-size: 12px; }}"
        )
        self._output.setPlaceholderText(
            "Ready — enter a command to begin."
        )
        layout.addWidget(self._output, 1)

        # ── Input Bar ──
        input_bar = QFrame()
        input_bar.setStyleSheet(
            f"background-color: {COLORS['bg_surface']}; "
            f"border-top: 1px solid {COLORS['border_hairline']};"
        )
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(16, 8, 16, 8)
        input_layout.setSpacing(8)

        self._backend_combo = QComboBox()
        self._backend_combo.addItems(["native", "wsl2", "docker"])
        self._backend_combo.setCurrentText("wsl2")
        self._backend_combo.setMinimumWidth(120)
        self._backend_combo.currentTextChanged.connect(self._update_title)
        input_layout.addWidget(self._backend_combo)

        self._cmd_input = QLineEdit()
        self._cmd_input.setPlaceholderText("Enter command (goes through policy validation)...")
        self._cmd_input.setFont(QFont("JetBrains Mono", 12))
        self._cmd_input.returnPressed.connect(self._on_submit)
        input_layout.addWidget(self._cmd_input, 1)

        self._run_btn = QPushButton("Run")
        self._run_btn.setObjectName("primaryButton")
        self._run_btn.clicked.connect(self._on_submit)
        input_layout.addWidget(self._run_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self._output.clear)
        input_layout.addWidget(clear_btn)

        layout.addWidget(input_bar)

    def _update_title(self, backend: str) -> None:
        labels = {
            "wsl2": "wsl2 — kali",
            "docker": "docker — container",
            "native": "native — local",
        }
        self._title_label.setText(labels.get(backend, backend))

    def _on_submit(self) -> None:
        cmd = self._cmd_input.text().strip()
        if cmd:
            backend = self._backend_combo.currentText()
            self.append_output(f"\n[{backend}] $ {cmd}\n")
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
        self._run_btn.setText("Running..." if running else "Run")
