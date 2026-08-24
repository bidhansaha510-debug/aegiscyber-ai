from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import QTimer

from app.gui.theme import COLORS


class StatusBarWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(20)

        self._app_label = QLabel("AegisCyber AI v1.0.0")
        self._app_label.setStyleSheet(
            f"color: {COLORS['accent_cyan']}; font-weight: 700; font-size: 12px;"
        )
        layout.addWidget(self._app_label)

        self._ollama_status = QLabel("● Ollama: Checking...")
        self._ollama_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self._ollama_status)

        self._backend_status = QLabel("● Backends: —")
        self._backend_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self._backend_status)

        self._gpu_label = QLabel("● GPU: —")
        self._gpu_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self._gpu_label)

        self._tool_count = QLabel("Tools: —")
        self._tool_count.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(self._tool_count)

        layout.addStretch()

        self._kill_status = QLabel("")
        self._kill_status.setStyleSheet(f"color: {COLORS['accent_red']}; font-weight: 700; font-size: 11px;")
        layout.addWidget(self._kill_status)

    def set_ollama_status(self, connected: bool, model: str = "") -> None:
        if connected:
            text = f"● Ollama: Connected ({model})" if model else "● Ollama: Connected"
            self._ollama_status.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 11px;")
        else:
            text = "● Ollama: Disconnected"
            self._ollama_status.setStyleSheet(f"color: {COLORS['accent_red']}; font-size: 11px;")
        self._ollama_status.setText(text)

    def set_backend_status(self, backends: dict[str, bool]) -> None:
        parts = []
        for name, available in backends.items():
            color = COLORS['accent_green'] if available else COLORS['text_muted']
            status = "✓" if available else "✗"
            parts.append(f"{status} {name}")
        self._backend_status.setText(f"● Backends: {', '.join(parts)}")
        any_available = any(backends.values())
        color = COLORS['accent_green'] if any_available else COLORS['accent_red']
        self._backend_status.setStyleSheet(f"color: {color}; font-size: 11px;")

    def set_gpu_status(self, available: bool, usage: int = 0) -> None:
        if available:
            bar = "█" * (usage // 10) + "░" * (10 - usage // 10)
            self._gpu_label.setText(f"● GPU: {bar} {usage}%")
            self._gpu_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 11px;")
        else:
            self._gpu_label.setText("● GPU: N/A")
            self._gpu_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")

    def set_tool_count(self, installed: int, total: int) -> None:
        self._tool_count.setText(f"Tools: {installed}/{total}")

    def set_kill_switch(self, engaged: bool) -> None:
        if engaged:
            self._kill_status.setText("⚠ EMERGENCY STOP ACTIVE")
        else:
            self._kill_status.setText("")
