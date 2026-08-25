from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import QTimer

from app.gui.theme import COLORS, FONT_MONO, FONT_SANS


class StatusBarWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setStyleSheet(
            f"background-color: {COLORS['bg_void']}; "
            f"border-top: 1px solid {COLORS['border_hairline']};"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        self._app_label = QLabel("AegisCyber AI v1.0.0")
        self._app_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-family: {FONT_MONO}; "
            f"font-size: 11px; font-weight: 600;"
        )
        layout.addWidget(self._app_label)

        self._tool_count = QLabel("")
        self._tool_count.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-family: {FONT_MONO}; "
            f"font-size: 11px;"
        )
        layout.addWidget(self._tool_count)

        layout.addStretch()

        self._kill_status = QLabel("")
        self._kill_status.setStyleSheet(
            f"color: {COLORS['state_caution']}; font-family: {FONT_MONO}; "
            f"font-weight: 700; font-size: 11px;"
        )
        layout.addWidget(self._kill_status)

    

    def set_ollama_status(self, connected: bool, model: str = "") -> None:
        pass

    def set_backend_status(self, backends: dict[str, bool]) -> None:
        pass

    def set_gpu_status(self, gpu_info: dict | bool, usage: int = 0) -> None:
        pass

    def set_tool_count(self, installed: int, total: int) -> None:
        self._tool_count.setText(f"Tools {installed}/{total}")

    def set_kill_switch(self, engaged: bool) -> None:
        if engaged:
            self._kill_status.setText("⚠ EMERGENCY STOP ACTIVE")
        else:
            self._kill_status.setText("")
