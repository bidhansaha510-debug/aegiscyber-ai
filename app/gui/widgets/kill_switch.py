from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QWidget, QHBoxLayout
from PySide6.QtCore import Signal

from app.gui.theme import COLORS


class KillSwitchButton(QWidget):
    kill_switch_activated = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._button = QPushButton("⚡ EMERGENCY STOP")
        self._button.setObjectName("dangerButton")
        self._button.setMinimumHeight(40)
        self._button.setMinimumWidth(180)
        self._button.setStyleSheet(
            f"QPushButton#dangerButton {{ "
            f"background-color: {COLORS['kill_switch_bg']}; "
            f"border: 2px solid {COLORS['accent_red']}; "
            f"color: {COLORS['accent_red']}; "
            f"font-weight: 800; font-size: 13px; "
            f"border-radius: 8px; padding: 8px 20px; }}"
            f"QPushButton#dangerButton:hover {{ "
            f"background-color: {COLORS['accent_red']}; "
            f"color: white; }}"
        )
        self._button.clicked.connect(self._on_click)
        layout.addWidget(self._button)

        self._is_engaged = False

    def _on_click(self) -> None:
        self.kill_switch_activated.emit()

    def set_engaged(self, engaged: bool) -> None:
        self._is_engaged = engaged
        if engaged:
            self._button.setText("🔴 STOP ACTIVE - Click to Disengage")
            self._button.setStyleSheet(
                f"QPushButton#dangerButton {{ "
                f"background-color: {COLORS['accent_red']}; "
                f"border: 2px solid {COLORS['accent_red']}; "
                f"color: white; font-weight: 800; font-size: 13px; "
                f"border-radius: 8px; padding: 8px 20px; }}"
                f"QPushButton#dangerButton:hover {{ "
                f"background-color: {COLORS['kill_switch_bg']}; "
                f"color: {COLORS['accent_red']}; }}"
            )
        else:
            self._button.setText("⚡ EMERGENCY STOP")
            self._button.setStyleSheet(
                f"QPushButton#dangerButton {{ "
                f"background-color: {COLORS['kill_switch_bg']}; "
                f"border: 2px solid {COLORS['accent_red']}; "
                f"color: {COLORS['accent_red']}; "
                f"font-weight: 800; font-size: 13px; "
                f"border-radius: 8px; padding: 8px 20px; }}"
                f"QPushButton#dangerButton:hover {{ "
                f"background-color: {COLORS['accent_red']}; "
                f"color: white; }}"
            )
