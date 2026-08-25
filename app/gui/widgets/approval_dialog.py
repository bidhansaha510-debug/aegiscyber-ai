from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QWidget,
)
from PySide6.QtCore import Signal

from app.gui.theme import COLORS, RISK_COLORS, FONT_SANS, FONT_MONO


class ApprovalDialog(QDialog):
    approved = Signal(bool)

    def __init__(
        self,
        command: str,
        tool_name: str,
        target: str,
        risk_level: str,
        explanation: str,
        warnings: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command Approval Required")
        self.setMinimumSize(550, 350)
        self.setStyleSheet(
            f"QDialog {{ background-color: {COLORS['bg_surface']}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        risk_color = RISK_COLORS.get(risk_level, COLORS["state_review"])

        title = QLabel(f"⚠  Approval Required — {risk_level}")
        title.setStyleSheet(
            f"font-family: {FONT_SANS}; font-size: 18px; font-weight: 700; "
            f"color: {risk_color}; padding: 8px 0;"
        )
        layout.addWidget(title)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        info_layout.addWidget(self._info_label("Tool:", tool_name))
        info_layout.addWidget(self._info_label("Target:", target))
        info_layout.addWidget(self._info_label("Risk:", risk_level, risk_color))
        layout.addLayout(info_layout)

        cmd_label = QLabel("Command:")
        cmd_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-family: {FONT_SANS}; "
            f"font-weight: 600; font-size: 12px;"
        )
        layout.addWidget(cmd_label)

        cmd_display = QTextEdit()
        cmd_display.setPlainText(command)
        cmd_display.setReadOnly(True)
        cmd_display.setMaximumHeight(80)
        cmd_display.setStyleSheet(
            f"font-family: {FONT_MONO}; background-color: {COLORS['bg_void']}; "
            f"color: {COLORS['text_primary']}; font-size: 12px; "
            f"border: 1px solid {COLORS['border_hairline']}; border-radius: 8px; "
            f"padding: 8px;"
        )
        layout.addWidget(cmd_display)

        if explanation:
            exp_label = QLabel(f"Explanation: {explanation}")
            exp_label.setWordWrap(True)
            exp_label.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-family: {FONT_SANS}; "
                f"font-size: 12px; padding: 4px 0;"
            )
            layout.addWidget(exp_label)

        if warnings:
            for warning in warnings:
                warn_label = QLabel(f"⚠ {warning}")
                warn_label.setWordWrap(True)
                warn_label.setStyleSheet(
                    f"color: {COLORS['state_review']}; font-family: {FONT_SANS}; "
                    f"font-size: 12px; padding: 8px; "
                    f"background-color: {COLORS['bg_surface_raised']}; "
                    f"border-radius: 4px;"
                )
                layout.addWidget(warn_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        deny_btn = QPushButton("Deny")
        deny_btn.setObjectName("secondaryButton")
        deny_btn.setMinimumWidth(120)
        deny_btn.clicked.connect(self._deny)
        btn_layout.addWidget(deny_btn)

        approve_btn = QPushButton("Approve")
        approve_btn.setObjectName("primaryButton")
        approve_btn.setMinimumWidth(120)
        approve_btn.clicked.connect(self._approve)
        btn_layout.addWidget(approve_btn)

        layout.addLayout(btn_layout)

    def _info_label(self, key: str, value: str, color: str = "") -> QLabel:
        label = QLabel(f"{key} {value}")
        c = color or COLORS["text_primary"]
        label.setStyleSheet(
            f"color: {c}; font-family: {FONT_SANS}; font-size: 13px; padding: 2px 0;"
        )
        return label

    def _approve(self) -> None:
        self.approved.emit(True)
        self.accept()

    def _deny(self) -> None:
        self.approved.emit(False)
        self.reject()
