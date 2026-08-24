from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame,
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QTextCursor

from app.gui.theme import COLORS


class LiveTerminalWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QFrame()
        header.setStyleSheet(
            f"background-color: {COLORS['bg_secondary']}; "
            f"border: 1px solid {COLORS['border']}; "
            f"border-top-left-radius: 8px; border-top-right-radius: 8px; "
            f"padding: 2px 8px;"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(8)

        title = QLabel("[>] LIVE EXECUTION TERMINAL")
        title.setStyleSheet(
            f"font-family: 'Cascadia Code', 'Consolas', monospace; "
            f"font-size: 12px; font-weight: 700; color: {COLORS['accent_cyan']}; "
            f"background: transparent;"
        )
        header_layout.addWidget(title)

        self._status_badge = QLabel("IDLE")
        self._status_badge.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {COLORS['text_muted']}; "
            f"background-color: {COLORS['bg_card']}; padding: 2px 6px; border-radius: 4px;"
        )
        header_layout.addWidget(self._status_badge)

        self._backend_badge = QLabel("wsl2: kali-linux")
        self._backend_badge.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {COLORS['accent_purple']}; "
            f"background-color: {COLORS['bg_card']}; padding: 2px 6px; border-radius: 4px;"
        )
        header_layout.addWidget(self._backend_badge)

        header_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(24)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_card']}; color: {COLORS['text_secondary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 2px 8px; font-size: 11px; }}"
            f"QPushButton:hover {{ color: {COLORS['text_primary']}; border-color: {COLORS['accent_cyan']}; }}"
        )
        clear_btn.clicked.connect(self.clear_output)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        self._output_box = QTextEdit()
        self._output_box.setReadOnly(True)
        self._output_box.setStyleSheet(
            f"QTextEdit {{ background-color: {COLORS['bg_primary']}; "
            f"color: {COLORS['accent_green']}; "
            f"font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace; "
            f"font-size: 12px; line-height: 1.4; "
            f"border: 1px solid {COLORS['border']}; border-top: none; "
            f"border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; "
            f"padding: 8px; }}"
        )
        layout.addWidget(self._output_box, 1)

        self._append_prompt("AegisCyber AI Live Terminal Initialized. Awaiting automated execution...")

    def _append_prompt(self, text: str) -> None:
        self._output_box.append(f"<span style='color: {COLORS['text_muted']};'>{text}</span>")

    def start_command(self, tool_name: str, backend: str, command: str) -> None:
        self._status_badge.setText(f"[RUNNING] {tool_name}")
        self._status_badge.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {COLORS['accent_yellow']}; "
            f"background-color: {COLORS['bg_card']}; padding: 2px 6px; border-radius: 4px;"
        )
        self._backend_badge.setText(backend)
        
        prompt_html = (
            f"<br><span style='color: {COLORS['accent_blue']}; font-weight: bold;'>[aegis@{backend}]$ </span>"
            f"<span style='color: {COLORS['text_bright']}; font-weight: bold;'>{command}</span>"
        )
        self._output_box.append(prompt_html)
        self._scroll_to_bottom()

    def append_chunk(self, chunk: str, is_error: bool = False) -> None:
        if not chunk:
            return
        color = COLORS["accent_red"] if is_error else COLORS["accent_green"]
        escaped = chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self._output_box.insertHtml(f"<span style='color: {color};'>{escaped}</span>")
        self._scroll_to_bottom()

    def finish_command(self, tool_name: str, success: bool, duration: float) -> None:
        status_text = "COMPLETED" if success else "FAILED"
        status_color = COLORS["accent_green"] if success else COLORS["accent_red"]
        
        self._status_badge.setText(status_text)
        self._status_badge.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {status_color}; "
            f"background-color: {COLORS['bg_card']}; padding: 2px 6px; border-radius: 4px;"
        )

        fin_html = (
            f"<br><span style='color: {status_color}; font-weight: bold;'>"
            f"[{'+' if success else '-'}] Process {tool_name} finished in {duration:.1f}s with status: {status_text}"
            f"</span>"
        )
        self._output_box.append(fin_html)
        self._scroll_to_bottom()

    def clear_output(self) -> None:
        self._output_box.clear()
        self._status_badge.setText("IDLE")
        self._status_badge.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {COLORS['text_muted']}; "
            f"background-color: {COLORS['bg_card']}; padding: 2px 6px; border-radius: 4px;"
        )
        self._append_prompt("Terminal cleared. Ready for next command...")

    def _scroll_to_bottom(self) -> None:
        cursor = self._output_box.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._output_box.setTextCursor(cursor)
