from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QTextCursor, QKeyEvent

from app.gui.theme import COLORS, FONT_SANS, FONT_MONO


class ChatMessage(QFrame):
    def __init__(self, role: str, content: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chatMessage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        is_user = role == "user"

        # Header — user = text_primary, AI = accent (one accent, not two)
        header = QLabel("You" if is_user else "AegisCyber AI")
        header_color = COLORS["text_primary"] if is_user else COLORS["accent"]
        header.setStyleSheet(
            f"color: {header_color}; font-family: {FONT_SANS}; "
            f"font-weight: 700; font-size: 12px; background: transparent;"
        )
        layout.addWidget(header)

        body = QLabel(content)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-family: {FONT_SANS}; "
            f"font-size: 13px; background: transparent; padding: 4px 0px;"
        )
        layout.addWidget(body)

        # Uniform card style — no colored left-borders
        bg = COLORS["bg_surface_raised"] if is_user else COLORS["bg_surface"]
        self.setStyleSheet(
            f"QFrame#chatMessage {{ background-color: {bg}; border-radius: 8px; "
            f"border: 1px solid {COLORS['border_hairline']}; }}"
        )


class ChatInputWidget(QWidget):
    message_submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask AegisCyber AI or enter a research prompt...")
        self._input.setStyleSheet(
            f"QLineEdit {{ background-color: {COLORS['bg_void']}; "
            f"color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_hairline']}; border-radius: 8px; "
            f"padding: 10px 16px; font-family: {FONT_SANS}; font-size: 13px; }}"
            f"QLineEdit:focus {{ border-color: {COLORS['accent']}; }}"
        )
        self._input.returnPressed.connect(self._send)
        layout.addWidget(self._input, 1)

        self._send_btn = QPushButton("Send")
        self._send_btn.setObjectName("primaryButton")
        self._send_btn.setMinimumHeight(40)
        self._send_btn.setMinimumWidth(80)
        self._send_btn.clicked.connect(self._send)
        layout.addWidget(self._send_btn)

    def _send(self) -> None:
        text = self._input.text().strip()
        if text:
            self.message_submitted.emit(text)
            self._input.clear()

    def set_enabled(self, enabled: bool) -> None:
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)


class ChatWidget(QWidget):
    message_submitted = Signal(str)
    message_sent = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QLabel("AI Investigation Chat")
        header.setStyleSheet(
            f"font-family: {FONT_SANS}; font-size: 14px; font-weight: 600; "
            f"color: {COLORS['text_primary']}; padding: 8px 4px; "
            f"background: transparent;"
        )
        layout.addWidget(header)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {COLORS['border_hairline']}; "
            f"border-radius: 8px; background-color: {COLORS['bg_void']}; }}"
        )

        self._messages_container = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(8, 8, 8, 8)
        self._messages_layout.setSpacing(8)
        self._messages_layout.addStretch()

        self._scroll_area.setWidget(self._messages_container)
        layout.addWidget(self._scroll_area, 1)

        self._input_widget = ChatInputWidget()
        self._input_widget.message_submitted.connect(self._on_message_submitted)
        layout.addWidget(self._input_widget)

    def _on_message_submitted(self, text: str) -> None:
        self.add_message("user", text)
        self.message_submitted.emit(text)
        self.message_sent.emit(text)

    def add_message(self, role: str, content: str) -> None:
        msg = ChatMessage(role, content)
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, msg)

        QTimer.singleShot(50, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))

    def append_message(self, role: str, content: str) -> None:
        self.add_message(role, content)

    def set_processing(self, processing: bool) -> None:
        self._input_widget.set_enabled(not processing)

    def set_loading(self, loading: bool) -> None:
        self.set_processing(loading)

    def clear_messages(self) -> None:
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
