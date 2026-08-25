from __future__ import annotations

import os
from typing import Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton, QFileDialog, QTextEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor

from app.gui.theme import COLORS, FONT_SANS, FONT_MONO

SEVERITY_COLORS = {
    "Critical": "#FF4444",
    "High": "#FF6B35",
    "Medium": "#FFB830",
    "Low": "#5EA1FF",
    "Informational": "#7C8494",
}


class POCCardWidget(QFrame):
    def __init__(self, poc_data: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pocCard")
        severity = poc_data.get("severity", "Informational")
        sev_color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["Informational"])

        self.setStyleSheet(
            f"QFrame#pocCard {{ background-color: {COLORS['bg_surface']}; "
            f"border: 1px solid {COLORS['border_hairline']}; border-radius: 10px; "
            f"border-left: 4px solid {sev_color}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        title_label = QLabel(poc_data.get("title", "Untitled Finding"))
        title_label.setWordWrap(True)
        title_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-family: {FONT_SANS}; "
            f"font-size: 14px; font-weight: 700; background: transparent;"
        )
        header_row.addWidget(title_label, 1)

        sev_badge = QLabel(severity.upper())
        sev_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sev_badge.setStyleSheet(
            f"background-color: {sev_color}; color: #FFFFFF; "
            f"font-family: {FONT_MONO}; font-size: 10px; font-weight: 700; "
            f"padding: 3px 10px; border-radius: 4px;"
        )
        sev_badge.setFixedHeight(20)
        header_row.addWidget(sev_badge)
        layout.addLayout(header_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(16)

        target_label = QLabel(f"Target: {poc_data.get('target', 'N/A')}")
        target_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-family: {FONT_MONO}; "
            f"font-size: 11px; background: transparent;"
        )
        meta_row.addWidget(target_label)

        tool_label = QLabel(f"Tool: {poc_data.get('tool_name', 'N/A')}")
        tool_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-family: {FONT_MONO}; "
            f"font-size: 11px; background: transparent;"
        )
        meta_row.addWidget(tool_label)
        meta_row.addStretch()
        layout.addLayout(meta_row)

        if poc_data.get("description"):
            desc_label = QLabel(poc_data["description"][:300])
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(
                f"color: {COLORS['text_primary']}; font-family: {FONT_SANS}; "
                f"font-size: 12px; background: transparent; padding-top: 4px;"
            )
            layout.addWidget(desc_label)

        if poc_data.get("proof_command"):
            cmd_frame = QFrame()
            cmd_frame.setStyleSheet(
                f"background-color: {COLORS['bg_void']}; "
                f"border: 1px solid {COLORS['border_hairline']}; "
                f"border-radius: 6px; padding: 8px;"
            )
            cmd_layout = QVBoxLayout(cmd_frame)
            cmd_layout.setContentsMargins(8, 6, 8, 6)

            cmd_header = QLabel("PROOF COMMAND")
            cmd_header.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-family: {FONT_MONO}; "
                f"font-size: 9px; font-weight: 700; letter-spacing: 1px; "
                f"background: transparent;"
            )
            cmd_layout.addWidget(cmd_header)

            cmd_text = QLabel(poc_data["proof_command"][:500])
            cmd_text.setWordWrap(True)
            cmd_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            cmd_text.setStyleSheet(
                f"color: {COLORS['state_clear']}; font-family: {FONT_MONO}; "
                f"font-size: 12px; background: transparent;"
            )
            cmd_layout.addWidget(cmd_text)
            layout.addWidget(cmd_frame)

        if poc_data.get("reproduction_steps"):
            steps_header = QLabel("REPRODUCTION STEPS")
            steps_header.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-family: {FONT_MONO}; "
                f"font-size: 9px; font-weight: 700; letter-spacing: 1px; "
                f"background: transparent; padding-top: 4px;"
            )
            layout.addWidget(steps_header)

            for i, step in enumerate(poc_data["reproduction_steps"][:10], 1):
                step_label = QLabel(f"  {i}. {step}")
                step_label.setWordWrap(True)
                step_label.setStyleSheet(
                    f"color: {COLORS['text_primary']}; font-family: {FONT_SANS}; "
                    f"font-size: 12px; background: transparent;"
                )
                layout.addWidget(step_label)

        details_sections = [
            ("IMPACT", poc_data.get("impact", "")),
            ("REMEDIATION", poc_data.get("remediation", "")),
        ]
        for section_title, section_text in details_sections:
            if section_text:
                sec_header = QLabel(section_title)
                sec_header.setStyleSheet(
                    f"color: {COLORS['text_muted']}; font-family: {FONT_MONO}; "
                    f"font-size: 9px; font-weight: 700; letter-spacing: 1px; "
                    f"background: transparent; padding-top: 6px;"
                )
                layout.addWidget(sec_header)

                sec_body = QLabel(section_text[:400])
                sec_body.setWordWrap(True)
                sec_body.setStyleSheet(
                    f"color: {COLORS['text_primary']}; font-family: {FONT_SANS}; "
                    f"font-size: 12px; background: transparent;"
                )
                layout.addWidget(sec_body)


class POCViewerWidget(QWidget):
    export_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(48)
        header.setStyleSheet(
            f"background-color: {COLORS['bg_surface']}; "
            f"border-bottom: 1px solid {COLORS['border_hairline']};"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(12)

        title = QLabel("PROOF OF CONCEPT")
        title.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 13px; font-weight: 700; "
            f"color: {COLORS['accent']}; letter-spacing: 1px; background: transparent;"
        )
        header_layout.addWidget(title)

        self._count_badge = QLabel("0 findings")
        self._count_badge.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 11px; font-weight: 600; "
            f"color: {COLORS['text_muted']}; background: transparent;"
        )
        header_layout.addWidget(self._count_badge)

        header_layout.addStretch()

        export_btn = QPushButton("Export Report")
        export_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_surface_raised']}; "
            f"color: {COLORS['text_primary']}; border: 1px solid {COLORS['border_hairline']}; "
            f"border-radius: 6px; padding: 4px 14px; font-family: {FONT_SANS}; "
            f"font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ border-color: {COLORS['accent']}; color: {COLORS['accent']}; }}"
        )
        export_btn.clicked.connect(self._on_export_clicked)
        header_layout.addWidget(export_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_surface_raised']}; "
            f"color: {COLORS['text_muted']}; border: 1px solid {COLORS['border_hairline']}; "
            f"border-radius: 6px; padding: 4px 10px; font-family: {FONT_SANS}; "
            f"font-size: 12px; }}"
            f"QPushButton:hover {{ border-color: {COLORS['state_caution']}; color: {COLORS['state_caution']}; }}"
        )
        clear_btn.clicked.connect(self.clear_pocs)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: {COLORS['bg_void']}; }}"
        )

        self._container = QWidget()
        self._container.setStyleSheet(f"background-color: {COLORS['bg_void']};")
        self._cards_layout = QVBoxLayout(self._container)
        self._cards_layout.setContentsMargins(16, 12, 16, 16)
        self._cards_layout.setSpacing(12)
        self._cards_layout.addStretch()

        self._idle_label = QLabel("No POC findings yet.\nRun an investigation to generate proof-of-concept reports.")
        self._idle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._idle_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-family: {FONT_SANS}; "
            f"font-size: 13px; padding: 40px; background: transparent;"
        )
        self._cards_layout.insertWidget(0, self._idle_label)

        self._scroll_area.setWidget(self._container)
        layout.addWidget(self._scroll_area, 1)

        self._poc_data: list[dict[str, Any]] = []
        self._markdown_content: str = ""

    def add_poc(self, poc_data: dict[str, Any]) -> None:
        self._idle_label.hide()
        self._poc_data.append(poc_data)

        card = POCCardWidget(poc_data)
        self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

        self._count_badge.setText(f"{len(self._poc_data)} finding{'s' if len(self._poc_data) != 1 else ''}")

        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))

    def add_pocs_batch(self, pocs: list[dict[str, Any]]) -> None:
        for poc in pocs:
            self.add_poc(poc)

    def set_markdown_content(self, markdown: str) -> None:
        self._markdown_content = markdown

    def clear_pocs(self) -> None:
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget() and item.widget() != self._idle_label:
                item.widget().deleteLater()
        self._poc_data.clear()
        self._markdown_content = ""
        self._count_badge.setText("0 findings")
        self._idle_label.show()

    def _on_export_clicked(self) -> None:
        if not self._markdown_content and not self._poc_data:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export POC Report",
            "aegiscyber_poc_report.md",
            "Markdown Files (*.md);;All Files (*)",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self._markdown_content or self._build_fallback_markdown())
            except Exception:
                pass

    def _build_fallback_markdown(self) -> str:
        lines = ["# AegisCyber AI - POC Report\n"]
        for i, poc in enumerate(self._poc_data, 1):
            lines.append(f"## #{i}: {poc.get('title', 'Finding')}")
            lines.append(f"**Severity:** {poc.get('severity', 'N/A')}")
            lines.append(f"**Target:** {poc.get('target', 'N/A')}")
            lines.append(f"**Tool:** {poc.get('tool_name', 'N/A')}\n")
            if poc.get("description"):
                lines.append(f"{poc['description']}\n")
            if poc.get("proof_command"):
                lines.append(f"```\n{poc['proof_command']}\n```\n")
            lines.append("---\n")
        return "\n".join(lines)

    def get_poc_count(self) -> int:
        return len(self._poc_data)
