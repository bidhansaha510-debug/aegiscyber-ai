from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont

from app.gui.theme import COLORS, FONT_SANS, FONT_MONO


# ─── Node Icons ─────────────────────────────────────────────────────
_ICONS = {
    "done":       "●",
    "complete":   "●",
    "active":     "◐",
    "running":    "◐",
    "pending":    "○",
    "failed":     "✕",
    "blocked":    "✕",
    "skipped":    "○",
    "awaiting_approval": "◐",
}

_STATUS_COLORS = {
    "done":       COLORS["state_clear"],
    "complete":   COLORS["state_clear"],
    "active":     COLORS["accent"],
    "running":    COLORS["accent"],
    "pending":    COLORS["text_muted"],
    "failed":     COLORS["state_caution"],
    "blocked":    COLORS["state_review"],
    "skipped":    COLORS["text_muted"],
    "awaiting_approval": COLORS["state_review"],
}

_STATUS_LABELS = {
    "done":       "done",
    "complete":   "done",
    "active":     "active",
    "running":    "active",
    "pending":    "pending",
    "failed":     "failed",
    "blocked":    "blocked",
    "skipped":    "skipped",
    "awaiting_approval": "approval",
}

_LINE_COLORS = {
    "done":       COLORS["state_clear"],
    "complete":   COLORS["state_clear"],
}


class PipelineNodeWidget(QFrame):
    """A single node in the vertical connected pipeline timeline."""

    def __init__(
        self,
        step: str,
        status: str,
        detail: str,
        is_last: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("pipelineNode")
        self.setStyleSheet("QFrame#pipelineNode { background: transparent; }")

        self._status = status
        self._is_active = status in ("active", "running")

        node_color = _STATUS_COLORS.get(status, COLORS["text_muted"])
        icon_char = _ICONS.get(status, "○")
        line_color = _LINE_COLORS.get(status, COLORS["border_hairline"])

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # ── Node Row: icon ━━ label          badge ──
        node_row = QHBoxLayout()
        node_row.setContentsMargins(0, 0, 0, 0)
        node_row.setSpacing(0)

        # Icon
        self._icon_label = QLabel(f"{icon_char}━━")
        self._icon_label.setStyleSheet(
            f"color: {node_color}; font-family: {FONT_MONO}; font-size: 14px; "
            f"font-weight: 700; background: transparent; padding: 0;"
        )
        self._icon_label.setFixedWidth(40)
        node_row.addWidget(self._icon_label)

        # Step label
        step_label = QLabel(step)
        step_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-family: {FONT_SANS}; "
            f"font-size: 13px; font-weight: 600; background: transparent; "
            f"padding-left: 4px;"
        )
        node_row.addWidget(step_label, 1)

        # Status badge pill
        badge_bg = node_color
        badge = QLabel(_STATUS_LABELS.get(status, status))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"background-color: {badge_bg}; color: #FFFFFF; "
            f"font-family: {FONT_MONO}; font-size: 10px; font-weight: 700; "
            f"padding: 2px 8px; border-radius: 4px;"
        )
        badge.setFixedHeight(18)
        node_row.addWidget(badge)

        outer_layout.addLayout(node_row)

        # ── Detail line (if any) ──
        if detail:
            detail_label = QLabel(detail)
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-family: {FONT_SANS}; "
                f"font-size: 11px; background: transparent; "
                f"padding: 2px 0px 2px 44px;"
            )
            outer_layout.addWidget(detail_label)

        # ── Connecting line to next node ──
        if not is_last:
            line_label = QLabel("┃")
            line_label.setStyleSheet(
                f"color: {line_color}; font-family: {FONT_MONO}; font-size: 14px; "
                f"background: transparent; padding: 0px 0px 0px 5px;"
            )
            line_label.setFixedHeight(20)
            outer_layout.addWidget(line_label)

        # ── Pulse animation for active nodes ──
        if self._is_active:
            self._pulse_timer = QTimer(self)
            self._pulse_timer.timeout.connect(self._pulse_tick)
            self._pulse_timer.start(800)
            self._pulse_state = True

    def _pulse_tick(self) -> None:
        self._pulse_state = not self._pulse_state
        opacity = 1.0 if self._pulse_state else 0.5
        node_color = _STATUS_COLORS.get(self._status, COLORS["accent"])
        # Simulate opacity via alpha in color
        if opacity < 1.0:
            # Parse hex color and apply alpha via lighter shade
            r = int(node_color[1:3], 16)
            g = int(node_color[3:5], 16)
            b = int(node_color[5:7], 16)
            # Blend toward bg_void (#0B0E14) at 50%
            bg_r, bg_g, bg_b = 0x0B, 0x0E, 0x14
            r = int(r * opacity + bg_r * (1 - opacity))
            g = int(g * opacity + bg_g * (1 - opacity))
            b = int(b * opacity + bg_b * (1 - opacity))
            faded = f"#{r:02X}{g:02X}{b:02X}"
        else:
            faded = node_color

        icon_char = _ICONS.get(self._status, "◐")
        self._icon_label.setText(f"{icon_char}━━")
        self._icon_label.setStyleSheet(
            f"color: {faded}; font-family: {FONT_MONO}; font-size: 14px; "
            f"font-weight: 700; background: transparent; padding: 0;"
        )


class ReasoningPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {COLORS['bg_surface']};"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──
        self._header = QLabel("AI Reasoning")
        self._header.setStyleSheet(
            f"font-family: {FONT_SANS}; font-size: 14px; font-weight: 600; "
            f"color: {COLORS['text_primary']}; padding: 12px 16px 8px 16px; "
            f"background: transparent;"
        )
        layout.addWidget(self._header)

        # ── Scroll area ──
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: {COLORS['bg_surface']}; }}"
        )

        self._container = QWidget()
        self._container.setStyleSheet(
            f"background-color: {COLORS['bg_surface']};"
        )
        self._steps_layout = QVBoxLayout(self._container)
        self._steps_layout.setContentsMargins(16, 8, 16, 16)
        self._steps_layout.setSpacing(0)
        self._steps_layout.addStretch()

        self._scroll_area.setWidget(self._container)
        layout.addWidget(self._scroll_area, 1)

        # ── Idle state ──
        self._idle_label = QLabel(
            "Awaiting task — submit a request\nto see the reasoning pipeline."
        )
        self._idle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._idle_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-family: {FONT_SANS}; "
            f"font-size: 12px; padding: 32px 16px; background: transparent;"
        )
        self._steps_layout.insertWidget(0, self._idle_label)

    def set_investigation_id(self, investigation_id: str) -> None:
        if investigation_id and investigation_id != "running...":
            self._header.setText(f"AI Reasoning  ·  {investigation_id}")
        elif investigation_id:
            self._header.setText("AI Reasoning  ·  Active")
        else:
            self._header.setText("AI Reasoning")

    def update_steps(self, reasoning_steps: list[dict]) -> None:
        self.update_state(reasoning_steps)

    def update_state(self, reasoning_steps: list[dict]) -> None:
        self._idle_label.hide()

        # Remove old nodes (keep the stretch at the end)
        while self._steps_layout.count() > 1:
            item = self._steps_layout.takeAt(0)
            if item.widget() and item.widget() != self._idle_label:
                item.widget().deleteLater()

        total = len(reasoning_steps)
        for i, step_data in enumerate(reasoning_steps):
            is_last = (i == total - 1)
            node = PipelineNodeWidget(
                step=step_data.get("step", ""),
                status=step_data.get("status", "pending"),
                detail=step_data.get("detail", ""),
                is_last=is_last,
            )
            self._steps_layout.insertWidget(
                self._steps_layout.count() - 1, node
            )

        # Auto-scroll to bottom
        QTimer.singleShot(50, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))

    def clear_steps(self) -> None:
        self.clear()

    def clear(self) -> None:
        while self._steps_layout.count() > 1:
            item = self._steps_layout.takeAt(0)
            if item.widget() and item.widget() != self._idle_label:
                item.widget().deleteLater()
        self._idle_label.show()
