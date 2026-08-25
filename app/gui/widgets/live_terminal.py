from __future__ import annotations

import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame,
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QTextCursor

from app.gui.theme import COLORS, FONT_MONO, FONT_SANS

ANSI_REGEX = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\([a-zA-Z]|\x1b\[\?[0-9;]*[a-zA-Z]')


class LiveTerminalWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet(
            f"background-color: {COLORS['bg_surface_raised']}; "
            f"border-bottom: 1px solid {COLORS['border_hairline']};"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)
        header_layout.setSpacing(8)

        title = QLabel("Live Terminal")
        title.setStyleSheet(
            f"font-family: {FONT_SANS}; font-size: 12px; font-weight: 600; "
            f"color: {COLORS['text_primary']}; background: transparent;"
        )
        header_layout.addWidget(title)

        self._status_badge = QLabel("IDLE")
        self._status_badge.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 10px; font-weight: 700; "
            f"color: {COLORS['text_muted']}; background-color: {COLORS['bg_surface']}; "
            f"padding: 2px 8px; border-radius: 4px;"
        )
        header_layout.addWidget(self._status_badge)

        self._backend_badge = QLabel("wsl2")
        self._backend_badge.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 10px; font-weight: 600; "
            f"color: {COLORS['text_muted']}; background-color: {COLORS['bg_surface']}; "
            f"padding: 2px 8px; border-radius: 4px;"
        )
        header_layout.addWidget(self._backend_badge)

        header_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.setFixedHeight(22)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {COLORS['text_muted']}; "
            f"border: 1px solid {COLORS['border_hairline']}; border-radius: 4px; "
            f"padding: 2px 8px; font-family: {FONT_SANS}; font-size: 11px; }}"
            f"QPushButton:hover {{ color: {COLORS['text_primary']}; border-color: {COLORS['accent']}; }}"
        )
        clear_btn.clicked.connect(self.clear_output)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        self._output_box = QTextEdit()
        self._output_box.setReadOnly(True)
        self._output_box.setStyleSheet(
            f"QTextEdit {{ background-color: {COLORS['bg_void']}; "
            f"color: {COLORS['text_primary']}; "
            f"font-family: {FONT_MONO}; font-size: 12px; line-height: 1.4; "
            f"border: none; border-radius: 0px; padding: 8px; }}"
        )
        layout.addWidget(self._output_box, 1)

        self._append_system(
            "Awaiting automated execution — commands will stream here in real time."
        )

    def _append_system(self, text: str) -> None:
        self._output_box.append(
            f"<span style='color: {COLORS['text_muted']};'>{text}</span>"
        )

    def start_command(self, tool_name: str, backend: str, command: str) -> None:
        self._status_badge.setText(f"RUNNING  {tool_name}")
        self._status_badge.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 10px; font-weight: 700; "
            f"color: {COLORS['state_review']}; background-color: {COLORS['bg_surface']}; "
            f"padding: 2px 8px; border-radius: 4px;"
        )
        self._backend_badge.setText(backend)

        prompt_html = (
            f"<br><span style='color: {COLORS['accent']}; font-weight: bold;'>"
            f"[aegis@{backend}]$ </span>"
            f"<span style='color: {COLORS['text_primary']}; font-weight: bold;'>"
            f"{command}</span><br>"
        )
        self._output_box.append(prompt_html)
        self._scroll_to_bottom()

    def append_chunk(self, chunk: str, is_error: bool = False) -> None:
        if not chunk:
            return
        clean_chunk = ANSI_REGEX.sub('', chunk)
        if not clean_chunk:
            return
        color = COLORS["state_caution"] if is_error else COLORS["text_primary"]
        escaped = (
            clean_chunk
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        self._output_box.insertHtml(
            f"<span style='color: {color};'>{escaped}</span>"
        )
        self._scroll_to_bottom()

    def finish_command(self, tool_name: str, success: bool, duration: float) -> None:
        status_text = "COMPLETED" if success else "FAILED"
        status_color = COLORS["state_clear"] if success else COLORS["state_caution"]

        self._status_badge.setText(status_text)
        self._status_badge.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 10px; font-weight: 700; "
            f"color: {status_color}; background-color: {COLORS['bg_surface']}; "
            f"padding: 2px 8px; border-radius: 4px;"
        )

        fin_html = (
            f"<br><span style='color: {status_color}; font-weight: bold;'>"
            f"{'●' if success else '✕'} {tool_name} finished in {duration:.1f}s — "
            f"{status_text}</span><br>"
        )
        self._output_box.append(fin_html)
        self._scroll_to_bottom()

    def clear_output(self) -> None:
        self._output_box.clear()
        self._status_badge.setText("IDLE")
        self._status_badge.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 10px; font-weight: 600; "
            f"color: {COLORS['text_muted']}; background-color: {COLORS['bg_surface']}; "
            f"padding: 2px 8px; border-radius: 4px;"
        )
        self._append_system("Terminal cleared. Ready for next command.")

    def _scroll_to_bottom(self) -> None:
        cursor = self._output_box.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._output_box.setTextCursor(cursor)
