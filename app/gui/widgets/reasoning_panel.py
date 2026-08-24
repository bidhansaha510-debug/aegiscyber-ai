from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea
from PySide6.QtCore import Qt

from app.gui.theme import COLORS


class ReasoningStepWidget(QFrame):
    def __init__(self, step: str, status: str, detail: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("reasoningStep")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        status_icons = {
            "pending": "○",
            "active": "◉",
            "running": "⟳",
            "complete": "✓",
            "failed": "✗",
            "blocked": "⊘",
            "skipped": "→",
            "awaiting_approval": "⏸",
        }
        status_colors = {
            "pending": COLORS["text_muted"],
            "active": COLORS["accent_cyan"],
            "running": COLORS["accent_blue"],
            "complete": COLORS["accent_green"],
            "failed": COLORS["accent_red"],
            "blocked": COLORS["accent_red"],
            "skipped": COLORS["text_muted"],
            "awaiting_approval": COLORS["accent_yellow"],
        }

        icon = status_icons.get(status, "○")
        color = status_colors.get(status, COLORS["text_muted"])

        step_label = QLabel(f"{icon} {step}")
        step_label.setStyleSheet(
            f"color: {color}; font-weight: 600; font-size: 12px; background: transparent;"
        )
        layout.addWidget(step_label)

        if detail:
            detail_label = QLabel(f"  → {detail}")
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 11px; "
                f"background: transparent; padding-left: 16px;"
            )
            layout.addWidget(detail_label)

        self.setStyleSheet(
            f"QFrame#reasoningStep {{ background-color: {COLORS['bg_card']}; "
            f"border-left: 2px solid {color}; border-radius: 4px; margin: 1px 0; }}"
        )


class ReasoningPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QLabel("🧠 AI Reasoning")
        header.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {COLORS['accent_purple']}; "
            f"padding: 8px 4px; background: transparent;"
        )
        layout.addWidget(header)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {COLORS['border']}; border-radius: 6px; "
            f"background-color: {COLORS['bg_primary']}; }}"
        )

        self._container = QWidget()
        self._steps_layout = QVBoxLayout(self._container)
        self._steps_layout.setContentsMargins(4, 4, 4, 4)
        self._steps_layout.setSpacing(4)
        self._steps_layout.addStretch()

        self._scroll_area.setWidget(self._container)
        layout.addWidget(self._scroll_area, 1)

        self._idle_label = QLabel("Awaiting task...")
        self._idle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._idle_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-style: italic; "
            f"padding: 20px; background: transparent;"
        )
        self._steps_layout.insertWidget(0, self._idle_label)

    def update_state(self, reasoning_steps: list[dict]) -> None:
        self._idle_label.hide()

        while self._steps_layout.count() > 1:
            item = self._steps_layout.takeAt(0)
            if item.widget() and item.widget() != self._idle_label:
                item.widget().deleteLater()

        for step_data in reasoning_steps:
            step_widget = ReasoningStepWidget(
                step=step_data.get("step", ""),
                status=step_data.get("status", "pending"),
                detail=step_data.get("detail", ""),
            )
            self._steps_layout.insertWidget(self._steps_layout.count() - 1, step_widget)

    def clear(self) -> None:
        while self._steps_layout.count() > 1:
            item = self._steps_layout.takeAt(0)
            if item.widget() and item.widget() != self._idle_label:
                item.widget().deleteLater()
        self._idle_label.show()
