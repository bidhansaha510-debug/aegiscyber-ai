from __future__ import annotations

from typing import Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QGroupBox, QProgressBar,
)
from PySide6.QtCore import Qt

from app.gui.theme import COLORS, FONT_SANS, FONT_MONO


class StatCard(QFrame):
    """Uniform instrument-readout card. No decorative color — numbers are
    --text-primary by default and only colored when they carry semantic
    meaning (e.g. an unavailable backend)."""

    def __init__(self, title: str, value: str, icon: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setMinimumSize(200, 96)
        self.setStyleSheet(
            f"QFrame#statCard {{ background-color: {COLORS['bg_surface_raised']}; "
            f"border: 1px solid {COLORS['border_hairline']}; border-radius: 8px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(4)

        header = QLabel(f"{icon}  {title}")
        header.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-family: {FONT_SANS}; "
            f"font-size: 11px; font-weight: 600; text-transform: uppercase; "
            f"background: transparent;"
        )
        layout.addWidget(header)

        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-family: {FONT_MONO}; "
            f"font-size: 28px; font-weight: 700; background: transparent;"
        )
        layout.addWidget(self._value_label)

    def set_value(self, value: str, color: str = "") -> None:
        c = color or COLORS["text_primary"]
        self._value_label.setText(value)
        self._value_label.setStyleSheet(
            f"color: {c}; font-family: {FONT_MONO}; "
            f"font-size: 28px; font-weight: 700; background: transparent;"
        )


class DashboardPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        title = QLabel("Dashboard")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {COLORS['text_primary']}; "
            f"font-family: {FONT_SANS};"
        )
        layout.addWidget(title)

        # ── Stat Cards ──
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self._investigations_card = StatCard("Investigations", "0", "◆")
        self._tools_card = StatCard("Tools Available", "0 / 25", "⚙")
        self._executions_card = StatCard("Commands Executed", "0", "▶")
        self._entities_card = StatCard("OSINT Entities", "0", "◎")

        cards_layout.addWidget(self._investigations_card)
        cards_layout.addWidget(self._tools_card)
        cards_layout.addWidget(self._executions_card)
        cards_layout.addWidget(self._entities_card)
        layout.addLayout(cards_layout)

        # ── Current Scope ──
        scope_card = QFrame()
        scope_card.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_surface_raised']}; "
            f"border: 1px solid {COLORS['border_hairline']}; border-radius: 8px; }}"
        )
        scope_layout = QVBoxLayout(scope_card)
        scope_layout.setContentsMargins(16, 16, 16, 16)
        scope_layout.setSpacing(8)

        scope_title = QLabel("Current Scope")
        scope_title.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-family: {FONT_SANS}; "
            f"font-size: 14px; font-weight: 600; background: transparent;"
        )
        scope_layout.addWidget(scope_title)

        self._scope_label = QLabel(
            "No scope defined — configure targets to begin."
        )
        self._scope_label.setWordWrap(True)
        self._scope_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-family: {FONT_SANS}; "
            f"font-size: 13px; background: transparent;"
        )
        scope_layout.addWidget(self._scope_label)
        scope_layout.addStretch()

        layout.addWidget(scope_card, 1)

    # ── Public API (unchanged signatures) ──

    def update_stats(
        self,
        investigations: int = 0,
        tools: int = 0,
        executions: int = 0,
        entities: int = 0,
    ) -> None:
        self._investigations_card.set_value(str(investigations))
        self._executions_card.set_value(str(executions))
        self._entities_card.set_value(str(entities))

    def update_tools_count(self, installed: int, total: int) -> None:
        self._tools_card.set_value(f"{installed} / {total}")

    def update_status(self, data: dict[str, Any]) -> None:
        # Stat values
        self._investigations_card.set_value(str(data.get("investigations_count", 0)))

        installed = data.get("installed_count", 0)
        total = data.get("tools_count", 0)
        tools_color = COLORS["state_caution"] if installed == 0 and total > 0 else ""
        self._tools_card.set_value(f"{installed} / {total}", tools_color)

        self._executions_card.set_value(str(data.get("executions_count", 0)))
        self._entities_card.set_value(str(data.get("entities_count", 0)))

    def update_system_status(
        self,
        ollama: bool = False,
        wsl: bool = False,
        docker: bool = False,
        gpu: dict | bool = False,
    ) -> None:
        # System status is now displayed in the header bar.
        # This method is kept for backward compatibility but is a no-op.
        pass

    def _set_status_label(self, label: QLabel, name: str, available: bool) -> None:
        # No-op — system status moved to header.
        pass

    def update_scope(self, scope_text: str) -> None:
        self._scope_label.setText(scope_text)
        self._scope_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-family: {FONT_SANS}; "
            f"font-size: 13px; background: transparent;"
        )
