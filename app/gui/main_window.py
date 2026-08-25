from __future__ import annotations

import asyncio
import sys
from typing import Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QSplitter, QLabel, QMessageBox, QPushButton,
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject
from PySide6.QtGui import QIcon

from app.gui.theme import COLORS, get_main_stylesheet
from app.gui.widgets.chat_widget import ChatWidget
from app.gui.widgets.reasoning_panel import ReasoningPanel
from app.gui.widgets.live_terminal import LiveTerminalWidget
from app.gui.widgets.status_bar import StatusBarWidget
from app.gui.widgets.kill_switch import KillSwitchButton
from app.gui.widgets.scope_dialog import ScopeDialog
from app.gui.widgets.approval_dialog import ApprovalDialog
from app.gui.dashboard import DashboardPage
from app.gui.terminal_view import TerminalPage
from app.gui.tools_view import ToolsPage
from app.gui.logs_view import LogsPage
from app.gui.settings_view import SettingsPage
from app.execution.hardware import get_gpu_info
from app.execution.models import ExecutionUpdate
from app.logging_config import get_logger

logger = get_logger("gui.main_window")


class AsyncBridge(QObject):
    coro_completed = Signal(object, object)
    coro_failed = Signal(object, str)
    reasoning_updated = Signal(list)
    approval_requested = Signal(object, object)
    live_output = Signal(str, bool)
    command_started = Signal(str, str, str)
    command_finished = Signal(str, bool, float)

    def __init__(self, loop: asyncio.AbstractEventLoop | None, parent=None):
        super().__init__(parent)
        self._loop = loop

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def run(self, coro, on_success=None, on_error=None):
        if not self._loop or not self._loop.is_running():
            if on_error:
                on_error("Async event loop is not running")
            return None

        def _done(future):
            try:
                result = future.result()
                self.coro_completed.emit(on_success, result)
            except Exception as e:
                self.coro_failed.emit(on_error, str(e))

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        future.add_done_callback(_done)
        return future


class MainWindow(QMainWindow):
    def __init__(self, orchestrator=None, loop: asyncio.AbstractEventLoop | None = None) -> None:
        super().__init__()
        self._orchestrator = orchestrator
        self._loop = loop
        self._bridge = AsyncBridge(self._loop, self)
        self._bridge.coro_completed.connect(self._handle_coro_completed)
        self._bridge.coro_failed.connect(self._handle_coro_failed)
        self._bridge.reasoning_updated.connect(self._handle_reasoning_updated)
        self._bridge.approval_requested.connect(self._handle_approval_request)
        self._bridge.live_output.connect(self._handle_live_output)
        self._bridge.command_started.connect(self._handle_command_started)
        self._bridge.command_finished.connect(self._handle_command_finished)

        self._setup_window()
        self._build_ui()
        self._connect_signals()

        if self._orchestrator:
            self._orchestrator.on_reasoning_update(self._on_reasoning_step)
            self._orchestrator.set_approval_handler(self._on_orchestrator_approval_needed)
            self._orchestrator._exec_manager.on_update(self._on_exec_update)
            self._orchestrator.on_command_started(lambda t, b, c: self._bridge.command_started.emit(t, b, c))
            self._orchestrator.on_command_finished(lambda t, s, d: self._bridge.command_finished.emit(t, s, d))
            self._load_tools_table()
            self._on_scan_tools()

        self._start_status_timer()

    def _setup_window(self) -> None:
        self.setWindowTitle("AegisCyber AI - Cybersecurity Research Assistant")
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

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._dashboard = DashboardPage()
        self._tabs.addTab(self._dashboard, "Dashboard")

        self._investigation_panel = self._build_investigation_panel()
        self._tabs.addTab(self._investigation_panel, "Investigation")

        self._terminal = TerminalPage()
        self._tabs.addTab(self._terminal, "Terminal")

        self._tools_page = ToolsPage()
        self._tabs.addTab(self._tools_page, "Tools")

        self._logs_page = LogsPage()
        self._tabs.addTab(self._logs_page, "Logs & Audit")

        self._settings_page = SettingsPage()
        self._tabs.addTab(self._settings_page, "Settings")

        left_layout.addWidget(self._tabs)
        content_splitter.addWidget(left_panel)

        self._reasoning_panel = ReasoningPanel()
        self._reasoning_panel.setMinimumWidth(320)
        self._reasoning_panel.setMaximumWidth(450)
        content_splitter.addWidget(self._reasoning_panel)

        content_splitter.setStretchFactor(0, 7)
        content_splitter.setStretchFactor(1, 3)

        main_layout.addWidget(content_splitter, 1)

        self._status_bar = StatusBarWidget()
        main_layout.addWidget(self._status_bar)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(
            f"background-color: {COLORS['bg_secondary']}; "
            f"border-bottom: 1px solid {COLORS['border']};"
        )
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        logo = QLabel("AEGISCYBER AI")
        logo.setStyleSheet(
            f"font-size: 16px; font-weight: 800; color: {COLORS['accent_cyan']}; "
            f"letter-spacing: 2px;"
        )
        layout.addWidget(logo)

        tagline = QLabel("LOCAL SECURITY RESEARCH & RECON ASSISTANT")
        tagline.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {COLORS['text_muted']}; "
            f"letter-spacing: 1px;"
        )
        layout.addWidget(tagline)

        layout.addStretch()

        scope_btn = QPushButton("Target Scope")
        scope_btn.setToolTip("Configure authorized targets")
        scope_btn.clicked.connect(self._open_scope_dialog)
        layout.addWidget(scope_btn)

        self._kill_switch = KillSwitchButton()
        self._kill_switch.clicked.connect(self._on_kill_switch)
        layout.addWidget(self._kill_switch)

        return header

    def _build_investigation_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Vertical)
        
        self._chat = ChatWidget()
        splitter.addWidget(self._chat)

        self._live_terminal = LiveTerminalWidget()
        splitter.addWidget(self._live_terminal)

        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

        layout.addWidget(splitter)
        return panel

    def _connect_signals(self) -> None:
        self._chat.message_sent.connect(self._on_chat_message)
        self._terminal.command_submitted.connect(self._on_terminal_command)
        self._tools_page.scan_requested.connect(self._on_scan_tools)
        self._settings_page.settings_changed.connect(self._on_settings_changed)

    def _on_exec_update(self, update: ExecutionUpdate) -> None:
        if update.stdout_chunk:
            self._bridge.live_output.emit(update.stdout_chunk, False)
        if update.stderr_chunk:
            self._bridge.live_output.emit(update.stderr_chunk, True)

    @Slot(str, bool)
    def _handle_live_output(self, chunk: str, is_error: bool) -> None:
        self._live_terminal.append_chunk(chunk, is_error)

    @Slot(str, str, str)
    def _handle_command_started(self, tool: str, backend: str, cmd: str) -> None:
        self._live_terminal.start_command(tool, backend, cmd)

    @Slot(str, bool, float)
    def _handle_command_finished(self, tool: str, success: bool, duration: float) -> None:
        self._live_terminal.finish_command(tool, success, duration)
        self._update_status()

    def _start_status_timer(self) -> None:
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(5000)
        self._update_status()

    def _update_status(self) -> None:
        if not self._orchestrator or not self._loop:
            return

        async def _check():
            try:
                ollama_ok = await self._orchestrator._ollama.health_check()
            except Exception:
                ollama_ok = False

            backends = {}
            if self._orchestrator._exec_manager:
                try:
                    backends = await self._orchestrator._exec_manager.refresh_backend_availability()
                except Exception:
                    backends = {
                        b: self._orchestrator._exec_manager.is_backend_available(b)
                        for b in ["native", "wsl2", "docker"]
                    }

            tools_count = len(self._orchestrator._tool_registry.get_all_tools())
            installed_count = len(self._orchestrator._tool_registry.get_installed_tools())
            investigations_count = len(self._orchestrator._memory._investigations) if self._orchestrator else 0
            executions_count = len(self._orchestrator._exec_manager.get_all_executions()) if self._orchestrator else 0
            entities_count = self._orchestrator._osint_engine._graph.get_entity_count() if self._orchestrator else 0

            gpu_info = get_gpu_info()

            return {
                "ollama": ollama_ok,
                "model": getattr(self._orchestrator._ollama, "model", "llama3:latest"),
                "backends": backends,
                "tools_count": tools_count,
                "installed_count": installed_count,
                "investigations_count": investigations_count,
                "executions_count": executions_count,
                "entities_count": entities_count,
                "gpu": gpu_info,
            }

        self._bridge.run(
            _check(),
            on_success=self._on_status_result,
            on_error=lambda err: logger.warning("Status check failed: %s", err),
        )

    def _on_status_result(self, data: dict[str, Any]) -> None:
        self._status_bar.set_ollama_status(data["ollama"], data.get("model", "llama3:latest"))
        self._status_bar.set_backend_status(data["backends"])
        self._status_bar.set_tool_count(data["installed_count"], data["tools_count"])

        gpu_info = data.get("gpu", {})
        self._status_bar.set_gpu_status(gpu_info)

        ks = self._orchestrator._kill_switch.is_engaged if self._orchestrator else False
        self._status_bar.set_kill_switch(ks)

        self._dashboard.update_status(data)

    def _load_tools_table(self) -> None:
        if not self._orchestrator:
            return
        tools = self._orchestrator._tool_registry.get_all_tools()
        self._tools_page.populate_tools(tools)
        installed = self._orchestrator._tool_registry.get_installed_tools()
        self._dashboard.update_tools_count(len(installed), len(tools))

    def _on_reasoning_step(self, steps_data: list) -> None:
        self._bridge.reasoning_updated.emit(steps_data)

    def _on_orchestrator_approval_needed(self, command_plan: Any, policy: Any) -> bool:
        self._bridge.approval_requested.emit(command_plan, policy)
        return True

    @Slot(object, object)
    def _handle_approval_request(self, command_plan: Any, policy: Any) -> None:
        dialog = ApprovalDialog(
            command=command_plan.to_command_string(),
            tool_name=command_plan.executable,
            target=command_plan.target,
            risk_level=policy.risk,
            explanation=command_plan.explanation or "Security Tool Execution",
            warnings=policy.warnings,
            parent=self,
        )
        result = dialog.exec()
        approved = (result == ApprovalDialog.DialogCode.Accepted)
        if self._orchestrator:
            self._orchestrator.submit_approval_decision(approved)

    @Slot(list)
    def _handle_reasoning_updated(self, steps_data: list) -> None:
        self._reasoning_panel.update_steps(steps_data)

    def _on_chat_message(self, message: str) -> None:
        if not self._orchestrator or not self._loop:
            self._chat.append_message("system", "Orchestrator not initialized.")
            return

        self._chat.set_loading(True)
        self._reasoning_panel.clear_steps()
        self._reasoning_panel.set_investigation_id("running...")

        self._bridge.run(
            self._orchestrator.process_request(message),
            on_success=self._on_chat_response,
            on_error=self._on_chat_error,
        )

    def _on_chat_response(self, response: str) -> None:
        self._chat.append_message("assistant", response)
        self._chat.set_loading(False)
        if self._orchestrator:
            self._reasoning_panel.set_investigation_id(self._orchestrator.state.investigation_id)
        self._update_status()

    def _on_chat_error(self, error: str) -> None:
        self._chat.append_message("assistant", f"Error: {error}")
        self._chat.set_loading(False)
        self._update_status()

    @Slot(object, object)
    def _handle_coro_completed(self, callback, result):
        if callback:
            try:
                callback(result)
            except Exception as e:
                logger.error("Callback error: %s", e, exc_info=True)

    @Slot(object, str)
    def _handle_coro_failed(self, callback, error_str):
        if callback:
            try:
                callback(error_str)
            except Exception as e:
                logger.error("Error callback error: %s", e, exc_info=True)

    def _on_terminal_command(self, command: str) -> None:
        if not self._orchestrator or not self._loop:
            self._terminal.append_error("Execution manager not available")
            return

        self._terminal.set_running(True)

        async def _exec():
            from app.execution.models import CommandPlan, ExecutionRequest
            parts = command.strip().split()
            if not parts:
                return None
            plan = CommandPlan(
                executable=parts[0],
                arguments=parts[1:],
                backend="wsl2",
                timeout=1800,
            )
            req = ExecutionRequest(command_plan=plan)
            return await self._orchestrator._exec_manager.execute(req)

        self._bridge.run(
            _exec(),
            on_success=self._on_terminal_result,
            on_error=self._on_terminal_error,
        )

    def _on_terminal_result(self, result: Any) -> None:
        self._terminal.set_running(False)
        if not result:
            return
        if result.stdout:
            self._terminal.append_output(result.stdout)
        if result.stderr:
            self._terminal.append_error(result.stderr)
        if result.error_message:
            self._terminal.append_error(result.error_message)
        self._update_status()

    def _on_terminal_error(self, error: str) -> None:
        self._terminal.set_running(False)
        self._terminal.append_error(f"Error: {error}")

    def _on_scan_tools(self) -> None:
        if not self._orchestrator or not self._loop:
            return

        async def _scan():
            from app.tools.discovery import ToolDiscovery
            discovery = ToolDiscovery(
                self._orchestrator._tool_registry,
                self._orchestrator._exec_manager,
            )
            return await discovery.scan_all_tools()

        self._bridge.run(
            _scan(),
            on_success=self._on_tools_scanned,
            on_error=lambda err: logger.warning("Tool scan failed: %s", err),
        )

    def _on_tools_scanned(self, installed_list: list) -> None:
        self._load_tools_table()
        self._update_status()

    def _on_settings_changed(self, settings: dict) -> None:
        logger.info("Settings updated: %s", list(settings.keys()))

    def _open_scope_dialog(self) -> None:
        if not self._orchestrator:
            return
        dialog = ScopeDialog(self._orchestrator._auth_manager, parent=self)
        dialog.exec()
        scope_text = self._orchestrator._format_scope()
        self._dashboard.update_scope(scope_text)

    def _on_kill_switch(self) -> None:
        if not self._orchestrator:
            return
        ks = self._orchestrator._kill_switch
        if ks.is_engaged:
            ks.disengage()
            self._status_bar.set_kill_switch(False)
            self._chat.append_message("system", "Kill switch disengaged. System restored.")
        else:
            ks.engage("User activated kill switch")
            self._status_bar.set_kill_switch(True)
            self._chat.append_message("system", "EMERGENCY STOP ACTIVATED. All executions halted.")
