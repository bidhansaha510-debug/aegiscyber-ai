from __future__ import annotations

import asyncio
import sys
from typing import Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QSplitter, QLabel, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QThread
from PySide6.QtGui import QIcon

from app.gui.theme import COLORS, get_main_stylesheet
from app.gui.widgets.chat_widget import ChatWidget
from app.gui.widgets.reasoning_panel import ReasoningPanel
from app.gui.widgets.status_bar import StatusBarWidget
from app.gui.widgets.kill_switch import KillSwitchButton
from app.gui.widgets.scope_dialog import ScopeDialog
from app.gui.widgets.approval_dialog import ApprovalDialog
from app.gui.dashboard import DashboardPage
from app.gui.terminal_view import TerminalPage
from app.gui.tools_view import ToolsPage
from app.gui.logs_view import LogsPage
from app.gui.settings_view import SettingsPage
from app.logging_config import get_logger

logger = get_logger("gui.main_window")


class AsyncWorker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, coro, parent=None):
        super().__init__(parent)
        self._coro = coro
        self._loop = None

    def run(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            result = self._loop.run_until_complete(self._coro)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if self._loop:
                self._loop.close()


class MainWindow(QMainWindow):
    def __init__(self, orchestrator=None) -> None:
        super().__init__()
        self._orchestrator = orchestrator
        self._workers: list[AsyncWorker] = []
        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._start_status_timer()

    def _setup_window(self) -> None:
        self.setWindowTitle("AegisCyber AI — Cybersecurity Research Assistant")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        self.setStyleSheet(get_main_stylesheet())

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = self._build_header()
        main_layout.addWidget(header)

        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setHandleWidth(2)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._dashboard = DashboardPage()
        self._tabs.addTab(self._dashboard, "📊 Dashboard")

        self._chat_panel = self._build_investigation_panel()
        self._tabs.addTab(self._chat_panel, "🔍 Investigation")

        self._terminal = TerminalPage()
        self._tabs.addTab(self._terminal, "🖥 Terminal")

        self._tools_page = ToolsPage()
        self._tabs.addTab(self._tools_page, "🔧 Tools")

        self._logs_page = LogsPage()
        self._tabs.addTab(self._logs_page, "📋 Logs")

        self._settings_page = SettingsPage()
        self._tabs.addTab(self._settings_page, "⚙ Settings")

        left_layout.addWidget(self._tabs)
        content_splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_panel.setMinimumWidth(300)
        right_panel.setMaximumWidth(450)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)

        self._reasoning_panel = ReasoningPanel()
        right_layout.addWidget(self._reasoning_panel, 1)

        self._kill_switch = KillSwitchButton()
        right_layout.addWidget(self._kill_switch)

        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([1200, 350])

        main_layout.addWidget(content_splitter, 1)

        self._status_bar = StatusBarWidget()
        self._status_bar.setFixedHeight(32)
        self._status_bar.setStyleSheet(
            f"background-color: {COLORS['bg_primary']}; "
            f"border-top: 1px solid {COLORS['border']};"
        )
        main_layout.addWidget(self._status_bar)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {COLORS['bg_primary']}, stop:1 {COLORS['bg_tertiary']}); "
            f"border-bottom: 1px solid {COLORS['border']};"
        )
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        logo_label = QLabel("⛨ AegisCyber AI")
        logo_label.setStyleSheet(
            f"font-size: 20px; font-weight: 800; "
            f"color: {COLORS['accent_cyan']}; background: transparent;"
        )
        layout.addWidget(logo_label)

        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; "
            f"padding-top: 6px; background: transparent;"
        )
        layout.addWidget(version_label)

        layout.addStretch()

        scope_btn = self._create_header_button("🎯 Scope", "scopeButton")
        scope_btn.clicked.connect(self._open_scope_dialog)
        layout.addWidget(scope_btn)

        return header

    def _create_header_button(self, text: str, name: str) -> QWidget:
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.setObjectName(name)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_tertiary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; "
            f"padding: 6px 14px; color: {COLORS['text_primary']}; font-size: 12px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['bg_hover']}; "
            f"border-color: {COLORS['accent_cyan']}; }}"
        )
        return btn

    def _build_investigation_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._chat_widget = ChatWidget()
        layout.addWidget(self._chat_widget, 1)

        return panel

    def _connect_signals(self) -> None:
        self._chat_widget.message_submitted.connect(self._on_chat_submit)
        self._terminal.command_submitted.connect(self._on_terminal_command)
        self._kill_switch.kill_switch_activated.connect(self._on_kill_switch)
        self._settings_page.settings_changed.connect(self._on_settings_changed)

    def _start_status_timer(self) -> None:
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(10000)
        QTimer.singleShot(500, self._initial_status_check)

    def _initial_status_check(self) -> None:
        self._update_status()

    def _update_status(self) -> None:
        if self._orchestrator:
            worker = AsyncWorker(self._check_status_async())
            worker.finished.connect(self._on_status_checked)
            worker.start()
            self._workers.append(worker)

    async def _check_status_async(self) -> dict:
        result = {"ollama": False, "model": ""}
        if self._orchestrator:
            from app.ai.ollama_client import OllamaClient
            client = self._orchestrator._ollama
            result["ollama"] = await client.health_check()
            if result["ollama"]:
                from app.config import get_config
                result["model"] = get_config().ollama.model
        return result

    @Slot(object)
    def _on_status_checked(self, result: dict) -> None:
        self._status_bar.set_ollama_status(
            result.get("ollama", False),
            result.get("model", ""),
        )

    @Slot(str)
    def _on_chat_submit(self, message: str) -> None:
        self._chat_widget.add_message("user", message)
        self._chat_widget.set_processing(True)

        if self._orchestrator:
            worker = AsyncWorker(self._orchestrator.process_request(message))
            worker.finished.connect(self._on_chat_response)
            worker.error.connect(self._on_chat_error)
            worker.start()
            self._workers.append(worker)
        else:
            self._chat_widget.add_message("assistant", "Orchestrator not initialized. Please check Ollama connection.")
            self._chat_widget.set_processing(False)

    @Slot(object)
    def _on_chat_response(self, response: str) -> None:
        self._chat_widget.add_message("assistant", str(response))
        self._chat_widget.set_processing(False)

        if self._orchestrator:
            steps = [
                {"step": s.step, "status": s.status, "detail": s.detail}
                for s in self._orchestrator.state.reasoning_steps
            ]
            self._reasoning_panel.update_state(steps)

    @Slot(str)
    def _on_chat_error(self, error: str) -> None:
        self._chat_widget.add_message("assistant", f"Error: {error}")
        self._chat_widget.set_processing(False)

    @Slot(str, str)
    def _on_terminal_command(self, command: str, backend: str) -> None:
        self._terminal.set_running(True)
        self._terminal.append_output(f"Executing on {backend}...")

        if self._orchestrator:
            from app.execution.models import CommandPlan, ExecutionRequest
            parts = command.split()
            cmd_plan = CommandPlan(
                executable=parts[0] if parts else command,
                arguments=parts[1:] if len(parts) > 1 else [],
                target="",
                backend=backend,
            )

            policy = self._orchestrator._policy_engine.evaluate(cmd_plan)
            if not policy.allowed:
                self._terminal.append_error(f"BLOCKED: {policy.reason}")
                self._terminal.set_running(False)
                return

            if policy.requires_approval:
                dialog = ApprovalDialog(
                    command=command,
                    tool_name=parts[0] if parts else "unknown",
                    target="",
                    risk_level=policy.risk,
                    explanation="Terminal command",
                    warnings=policy.warnings,
                    parent=self,
                )
                if dialog.exec() != dialog.DialogCode.Accepted:
                    self._terminal.append_output("Command denied by user.")
                    self._terminal.set_running(False)
                    return

            exec_req = ExecutionRequest(task_id="terminal", command_plan=cmd_plan)
            worker = AsyncWorker(self._orchestrator._exec_manager.execute(exec_req))
            worker.finished.connect(self._on_terminal_result)
            worker.error.connect(self._on_terminal_error)
            worker.start()
            self._workers.append(worker)
        else:
            self._terminal.append_error("Orchestrator not initialized")
            self._terminal.set_running(False)

    @Slot(object)
    def _on_terminal_result(self, result) -> None:
        if result.stdout:
            self._terminal.append_output(result.stdout)
        if result.stderr:
            self._terminal.append_error(result.stderr)
        self._terminal.append_output(f"\n[Exit Code: {result.exit_code}] [{result.duration_seconds:.1f}s]\n")
        self._terminal.set_running(False)

    @Slot(str)
    def _on_terminal_error(self, error: str) -> None:
        self._terminal.append_error(error)
        self._terminal.set_running(False)

    def _on_kill_switch(self) -> None:
        if self._orchestrator:
            ks = self._orchestrator._kill_switch
            if ks.is_engaged:
                ks.disengage()
                self._kill_switch.set_engaged(False)
                self._status_bar.set_kill_switch(False)
                self._logs_page.append_log("[KILL SWITCH] Disengaged by user")
            else:
                ks.engage("User activated emergency stop")
                self._kill_switch.set_engaged(True)
                self._status_bar.set_kill_switch(True)
                self._logs_page.append_log("[KILL SWITCH] ENGAGED by user")

    def _open_scope_dialog(self) -> None:
        dialog = ScopeDialog(self)
        if self._orchestrator:
            scope = self._orchestrator._auth_manager.current_scope
            entries = [{"type": e.scope_type.value, "value": e.value} for e in scope.entries]
            dialog.set_entries(entries)
        dialog.scope_updated.connect(self._on_scope_updated)
        dialog.exec()

    def _on_scope_updated(self, entries: list[dict]) -> None:
        if self._orchestrator:
            from app.security.authorization import ScopeEntry, ScopeType, TargetScope, AuthorizationState
            scope_entries = []
            for entry in entries:
                scope_entries.append(ScopeEntry(
                    scope_type=ScopeType(entry["type"]),
                    value=entry["value"],
                ))
            target_scope = TargetScope(
                entries=scope_entries,
                state=AuthorizationState.USER_CONFIRMED,
            )
            self._orchestrator._auth_manager.set_scope(target_scope)
            scope_text = "\n".join(f"[{e['type']}] {e['value']}" for e in entries)
            self._dashboard.update_scope(scope_text)
            self._logs_page.append_log(f"[SCOPE] Updated: {len(entries)} entries")

    def _on_settings_changed(self, settings: dict) -> None:
        self._logs_page.append_log(f"[SETTINGS] Configuration updated")

    def closeEvent(self, event) -> None:
        for worker in self._workers:
            if worker.isRunning():
                worker.quit()
                worker.wait(1000)
        if self._orchestrator:
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self._orchestrator._ollama.close())
                loop.close()
            except Exception:
                pass
        event.accept()
