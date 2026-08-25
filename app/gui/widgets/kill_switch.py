from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QWidget, QHBoxLayout
from PySide6.QtCore import Signal

from app.gui.theme import COLORS, FONT_SANS


class KillSwitchButton(QWidget):
    kill_switch_activated = Signal()
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._button = QPushButton("EMERGENCY STOP")
        self._button.setObjectName("dangerButton")
        self._button.setMinimumHeight(36)
        self._button.setMinimumWidth(160)
        # No inline QSS — #dangerButton in theme.py handles everything
        self._button.clicked.connect(self._on_click)
        layout.addWidget(self._button)

        self._is_engaged = False

    def _on_click(self) -> None:
        self.kill_switch_activated.emit()
        self.clicked.emit()

    def set_engaged(self, engaged: bool) -> None:
        self._is_engaged = engaged
        if engaged:
            self._button.setText("⚠ STOP ACTIVE — Click to Disengage")
            # Override to show active state (filled caution)
            self._button.setStyleSheet(
                f"QPushButton#dangerButton {{ "
                f"background-color: {COLORS['state_caution']}; "
                f"border: 1px solid {COLORS['state_caution']}; "
                f"color: #FFFFFF; font-weight: 800; font-size: 13px; "
                f"font-family: {FONT_SANS}; "
                f"border-radius: 8px; padding: 8px 16px; }}"
                f"QPushButton#dangerButton:hover {{ "
                f"background-color: {COLORS['state_blocked']}; "
                f"color: {COLORS['state_caution']}; }}"
            )
        else:
            self._button.setText("EMERGENCY STOP")
            # Reset to default #dangerButton QSS from theme
            self._button.setStyleSheet("")
