from __future__ import annotations

import re

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSplitter,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.gui.theme import COLORS, FONT_MONO, FONT_SANS, get_main_stylesheet

ANSI_REGEX = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\([a-zA-Z]|\x1b\[\?[0-9;]*[a-zA-Z]')

_AUTO_CLOSE_SECONDS = 10
_MAX_CHUNK_CHARS = 4000
_MAX_EXCERPT_CHARS = 1500

_STATUS_COLORS = {
    "pending": COLORS["text_muted"],
    "active": COLORS["state_review"],
    "running": COLORS["accent"],
    "awaiting_approval": COLORS["state_review"],
    "complete": COLORS["state_clear"],
    "completed": COLORS["state_clear"],
    "skipped": COLORS["text_muted"],
    "failed": COLORS["state_caution"],
    "blocked": COLORS["state_caution"],
    "timeout": COLORS["state_caution"],
    "cancelled": COLORS["text_muted"],
}


def _esc(text: str) -> str:
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )


class SandboxAttackWindow(QWidget):
    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AegisCyber Sandbox — Live Attack View")
        self.setMinimumSize(920, 640)
        self.resize(1060, 720)
        if parent is not None:
            self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(get_main_stylesheet())

        self._seen_steps: dict[str, str] = {}
        self._commands: list[dict] = []
        self._finalized = False
        self._closed_emitted = False
        self._remaining = _AUTO_CLOSE_SECONDS

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(46)
        header.setStyleSheet(
            f"background-color: {COLORS['bg_surface']}; "
            f"border-bottom: 1px solid {COLORS['border_hairline']};"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 0, 14, 0)
        header_layout.setSpacing(12)

        title = QLabel("◉ SANDBOX")
        title.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 13px; font-weight: 800; "
            f"color: {COLORS['state_caution']}; letter-spacing: 2px; background: transparent;"
        )
        header_layout.addWidget(title)

        subtitle = QLabel("LIVE ATTACK VIEW")
        subtitle.setStyleSheet(
            f"font-family: {FONT_SANS}; font-size: 10px; font-weight: 600; "
            f"color: {COLORS['text_muted']}; letter-spacing: 1px; background: transparent;"
        )
        header_layout.addWidget(subtitle)

        self._target_label = QLabel("target: pending")
        self._target_label.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 11px; font-weight: 600; "
            f"color: {COLORS['text_primary']}; background: transparent;"
        )
        header_layout.addStretch()
        header_layout.addWidget(self._target_label)

        self._backend_badge = QLabel("—")
        self._backend_badge.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 10px; font-weight: 600; "
            f"color: {COLORS['text_muted']}; background-color: {COLORS['bg_surface_raised']}; "
            f"padding: 2px 8px; border-radius: 4px;"
        )
        header_layout.addWidget(self._backend_badge)

        self._status_badge = QLabel("PLANNING")
        self._status_badge.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 10px; font-weight: 700; "
            f"color: {COLORS['state_review']}; background-color: {COLORS['bg_surface_raised']}; "
            f"padding: 2px 10px; border-radius: 4px;"
        )
        header_layout.addWidget(self._status_badge)

        root.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Vertical)

        feed_frame = QFrame()
        feed_layout = QVBoxLayout(feed_frame)
        feed_layout.setContentsMargins(0, 0, 0, 0)
        feed_layout.setSpacing(0)

        feed_header = QLabel("  ATTACK FEED")
        feed_header.setFixedHeight(26)
        feed_header.setStyleSheet(
            f"font-family: {FONT_SANS}; font-size: 10px; font-weight: 700; "
            f"color: {COLORS['text_muted']}; letter-spacing: 1px; "
            f"background-color: {COLORS['bg_surface_raised']}; "
            f"border-bottom: 1px solid {COLORS['border_hairline']};"
        )
        feed_layout.addWidget(feed_header)

        self._feed = QTextEdit()
        self._feed.setReadOnly(True)
        self._feed.setStyleSheet(
            f"QTextEdit {{ background-color: {COLORS['bg_void']}; "
            f"color: {COLORS['text_primary']}; "
            f"font-family: {FONT_MONO}; font-size: 12px; line-height: 1.4; "
            f"border: none; padding: 8px; }}"
        )
        feed_layout.addWidget(self._feed, 1)
        splitter.addWidget(feed_frame)

        results_frame = QFrame()
        results_layout = QVBoxLayout(results_frame)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(0)

        results_header = QLabel("  COMMANDS & RESULTS")
        results_header.setFixedHeight(26)
        results_header.setStyleSheet(
            f"font-family: {FONT_SANS}; font-size: 10px; font-weight: 700; "
            f"color: {COLORS['text_muted']}; letter-spacing: 1px; "
            f"background-color: {COLORS['bg_surface_raised']}; "
            f"border-bottom: 1px solid {COLORS['border_hairline']};"
        )
        results_layout.addWidget(results_header)

        self._results = QTextEdit()
        self._results.setReadOnly(True)
        self._results.setStyleSheet(
            f"QTextEdit {{ background-color: {COLORS['bg_void']}; "
            f"color: {COLORS['text_primary']}; "
            f"font-family: {FONT_MONO}; font-size: 12px; line-height: 1.4; "
            f"border: none; padding: 8px; }}"
        )
        self._results.append(
            f"<span style='color: {COLORS['text_muted']};'>"
            f"The full command log with results will be printed here when the operation finishes."
            f"</span>"
        )
        results_layout.addWidget(self._results, 1)
        splitter.addWidget(results_frame)

        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        root.addWidget(splitter, 1)

        footer = QFrame()
        footer.setFixedHeight(42)
        footer.setStyleSheet(
            f"background-color: {COLORS['bg_surface']}; "
            f"border-top: 1px solid {COLORS['border_hairline']};"
        )
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 0, 14, 0)
        footer_layout.setSpacing(10)

        self._countdown_label = QLabel("")
        self._countdown_label.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 11px; font-weight: 600; "
            f"color: {COLORS['state_review']}; background: transparent;"
        )
        footer_layout.addWidget(self._countdown_label)
        footer_layout.addStretch()

        keep_btn = QPushButton("Keep Open")
        keep_btn.setObjectName("secondaryButton")
        keep_btn.setFixedHeight(26)
        keep_btn.clicked.connect(self._keep_open)
        footer_layout.addWidget(keep_btn)

        close_btn = QPushButton("Close Sandbox")
        close_btn.setObjectName("secondaryButton")
        close_btn.setFixedHeight(26)
        close_btn.clicked.connect(self.close_now)
        footer_layout.addWidget(close_btn)

        root.addWidget(footer)

        self._close_timer = QTimer(self)
        self._close_timer.setInterval(1000)
        self._close_timer.timeout.connect(self._tick_close)

        self._append_feed(
            "Sandbox initialized. AI attack operations will stream here in real time.",
            COLORS["text_muted"],
        )

    def start(self, request_text: str) -> None:
        self._seen_steps.clear()
        self._commands.clear()
        self._finalized = False
        self._remaining = _AUTO_CLOSE_SECONDS
        self._set_badge("PLANNING", COLORS["state_review"])
        self._append_feed(
            f"Request received: {request_text.strip()[:400]}",
            COLORS["text_primary"],
        )

    def update_reasoning_steps(self, steps: list) -> None:
        if self._finalized:
            return
        for step in steps:
            if not isinstance(step, dict):
                continue
            name = str(step.get("step", ""))
            status = str(step.get("status", ""))
            if not name:
                continue
            if self._seen_steps.get(name) == status:
                continue
            self._seen_steps[name] = status
            color = _STATUS_COLORS.get(status, COLORS["text_muted"])
            detail = str(step.get("detail", "") or "")
            line = f"[{status.upper()}] {name}"
            if detail:
                line += f" — {detail[:300]}"
            self._append_feed(line, color)

    def command_started(self, tool: str, backend: str, command: str) -> None:
        if self._finalized:
            return
        self._set_badge(f"RUNNING  {tool}", COLORS["accent"])
        self._backend_badge.setText(backend)
        self._append_feed(
            f"[aegis@{backend}]$ {command}",
            COLORS["accent"],
            bold=True,
        )

    def append_output_chunk(self, chunk: str, is_error: bool = False) -> None:
        if self._finalized or not chunk:
            return
        clean = ANSI_REGEX.sub('', chunk).replace('\r', '')
        if not clean:
            return
        if len(clean) > _MAX_CHUNK_CHARS:
            clean = clean[:_MAX_CHUNK_CHARS] + " …"
        color = COLORS["state_caution"] if is_error else COLORS["text_muted"]
        self._append_feed(clean, color)

    def command_result(self, result: dict) -> None:
        if self._finalized:
            return
        status = str(result.get("status", "completed"))
        tool = str(result.get("tool_name", "tool"))
        duration = float(result.get("duration_seconds", 0.0) or 0.0)
        target = str(result.get("target", "") or "")
        if target:
            self._target_label.setText(f"target: {target}")

        self._commands.append(result)
        if status == "completed":
            self._set_badge("COMPLETED", COLORS["state_clear"])
            self._append_feed(
                f"● {tool} finished in {duration:.1f}s",
                COLORS["state_clear"],
            )
        else:
            self._set_badge(status.upper(), COLORS["state_caution"])
            self._append_feed(
                f"✕ {tool} {status} in {duration:.1f}s",
                COLORS["state_caution"],
            )

    def finalize(self, reason: str) -> None:
        if self._finalized:
            return
        self._finalized = True
        self._set_badge("CLOSED", COLORS["state_caution"])
        self._append_feed(f"Sandbox closed — {reason}", COLORS["state_caution"], bold=True)
        self._print_final_log()
        self._remaining = _AUTO_CLOSE_SECONDS
        self._countdown_label.setText(f"Sandbox closing in {self._remaining}s")
        self._close_timer.start()

    def close_now(self) -> None:
        self._close_timer.stop()
        if not self._closed_emitted:
            self._closed_emitted = True
            self.closed.emit()
        self.close()
        self.deleteLater()

    def _keep_open(self) -> None:
        self._close_timer.stop()
        self._countdown_label.setText("")

    def _tick_close(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self.close_now()
            return
        self._countdown_label.setText(f"Sandbox closing in {self._remaining}s")

    def _print_final_log(self) -> None:
        self._results.clear()
        if not self._commands:
            self._results.append(
                f"<span style='color: {COLORS['state_review']}; font-weight: bold;'>"
                f"No commands were executed against the target."
                f"</span>"
            )
            return

        completed = sum(1 for c in self._commands if c.get("status") == "completed")
        header = (
            f"<span style='color: {COLORS['text_primary']}; font-weight: bold;'>"
            f"FINAL LOG — {len(self._commands)} command(s), {completed} completed"
            f"</span>"
        )
        self._results.append(header)

        for index, cmd in enumerate(self._commands, start=1):
            status = str(cmd.get("status", "unknown"))
            duration = float(cmd.get("duration_seconds", 0.0) or 0.0)
            exit_code = cmd.get("exit_code")
            status_color = COLORS["state_clear"] if status == "completed" else COLORS["state_caution"]

            block = [
                f"<br><span style='color: {COLORS['accent']}; font-weight: bold;'>"
                f"{index}. $ {_esc(str(cmd.get('command', '')))}"
                f"</span>"
            ]
            meta = f"status: {status} | duration: {duration:.1f}s"
            if exit_code is not None:
                meta += f" | exit: {exit_code}"
            meta += f" | backend: {cmd.get('backend', '—')}"
            block.append(
                f"<span style='color: {status_color};'>{_esc(meta)}</span>"
            )

            stdout = str(cmd.get("stdout", "") or "")
            stderr = str(cmd.get("stderr", "") or "")
            error_message = str(cmd.get("error_message", "") or "")
            body = stdout.strip() or stderr.strip() or error_message.strip()
            if body:
                body = ANSI_REGEX.sub('', body).replace('\r', '')
                if len(body) > _MAX_EXCERPT_CHARS:
                    body = body[:_MAX_EXCERPT_CHARS] + f"\n… output truncated ({len(body)} chars total)"
                block.append(
                    f"<span style='color: {COLORS['text_muted']};'>{_esc(body)}</span>"
                )
            self._results.append("<br>".join(block))

        self._scroll_to_bottom(self._results)

    def _set_badge(self, text: str, color: str) -> None:
        self._status_badge.setText(text)
        self._status_badge.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 10px; font-weight: 700; "
            f"color: {color}; background-color: {COLORS['bg_surface_raised']}; "
            f"padding: 2px 10px; border-radius: 4px;"
        )

    def _append_feed(self, text: str, color: str, bold: bool = False) -> None:
        weight = "font-weight: bold;" if bold else ""
        self._feed.append(
            f"<span style='color: {color}; {weight}'>{_esc(text)}</span>"
        )
        self._scroll_to_bottom(self._feed)

    def _scroll_to_bottom(self, box: QTextEdit) -> None:
        cursor = box.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        box.setTextCursor(cursor)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and not self._finalized:
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._close_timer.stop()
        if not self._closed_emitted:
            self._closed_emitted = True
            self.closed.emit()
        super().closeEvent(event)
