from __future__ import annotations

import asyncio
import os
import sys
import threading
from typing import Any

from PySide6.QtWidgets import QApplication

from app.config import get_config
from app.database.connection import DatabaseManager
from app.database.migrations import MigrationManager
from app.security.authorization import AuthorizationManager
from app.security.audit import AuditLogger
from app.security.kill_switch import KillSwitch
from app.security.secrets import SecretsManager
from app.execution.manager import ExecutionManager
from app.tools.registry import ToolRegistry
from app.tools.discovery import ToolDiscovery
from app.tools.policy import PolicyEngine
from app.tools.command_planner import CommandPlanner
from app.parsers.registry import ParserRegistry
from app.osint.engine import OSINTEngine
from app.osint.graph import KnowledgeGraph
from app.ai.ollama_client import OllamaClient
from app.ai.orchestrator import Orchestrator
from app.gui.main_window import MainWindow
from app.logging_config import setup_logging, get_logger


class AsyncLoopThread(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True, name="AegisAsyncLoopThread")
        self.loop: asyncio.AbstractEventLoop | None = None
        self.ready_event = threading.Event()

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.ready_event.set()
        self.loop.run_forever()

    def stop(self) -> None:
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


async def initialize_system() -> dict:
    config = get_config()
    logger = get_logger("main")
    logger.info("Initializing AegisCyber AI v1.0.0")

    db = DatabaseManager(config.database.db_path)
    await db.initialize()

    migrations = MigrationManager(db)
    await migrations.run_migrations()

    auth_manager = AuthorizationManager()
    audit_logger = AuditLogger(config.security.audit_log_path)
    audit_logger.set_database(db)
    kill_switch = KillSwitch()
    secrets_manager = SecretsManager()

    exec_manager = ExecutionManager(kill_switch=kill_switch)
    await exec_manager.initialize()
    tool_registry = ToolRegistry(config.tool_registry_dir)
    tools_loaded = tool_registry.load_all()
    logger.info("Loaded %d tool definitions", tools_loaded)

    tool_discovery = ToolDiscovery(tool_registry, exec_manager)
    await tool_discovery.scan_all_tools()

    policy_engine = PolicyEngine(auth_manager)
    command_planner = CommandPlanner(tool_registry)
    parser_registry = ParserRegistry()

    knowledge_graph = KnowledgeGraph()
    osint_engine = OSINTEngine(knowledge_graph, secrets_manager=secrets_manager)

    ollama_client = OllamaClient()

    orchestrator = Orchestrator(
        ollama_client=ollama_client,
        execution_manager=exec_manager,
        tool_registry=tool_registry,
        policy_engine=policy_engine,
        parser_registry=parser_registry,
        osint_engine=osint_engine,
        auth_manager=auth_manager,
        audit_logger=audit_logger,
        kill_switch=kill_switch,
    )

    logger.info("AegisCyber AI initialization complete")

    return {
        "config": config,
        "database": db,
        "auth_manager": auth_manager,
        "audit_logger": audit_logger,
        "kill_switch": kill_switch,
        "secrets_manager": secrets_manager,
        "execution_manager": exec_manager,
        "tool_registry": tool_registry,
        "tool_discovery": tool_discovery,
        "policy_engine": policy_engine,
        "command_planner": command_planner,
        "parser_registry": parser_registry,
        "knowledge_graph": knowledge_graph,
        "osint_engine": osint_engine,
        "ollama_client": ollama_client,
        "orchestrator": orchestrator,
    }


def main() -> None:
    config = get_config()
    setup_logging(log_dir=config.log_dir, debug=config.debug)
    logger = get_logger("main")

    async_thread = AsyncLoopThread()
    async_thread.start()
    async_thread.ready_event.wait(timeout=5.0)

    if not async_thread.loop:
        logger.critical("Failed to start background async event loop thread")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("AegisCyber AI")
    app.setOrganizationName("AegisCyber")

    future = asyncio.run_coroutine_threadsafe(initialize_system(), async_thread.loop)
    try:
        components = future.result(timeout=15.0)
    except Exception as e:
        logger.critical("System initialization failed: %s", e, exc_info=True)
        sys.exit(1)

    orchestrator = components.get("orchestrator")
    window = MainWindow(orchestrator=orchestrator, loop=async_thread.loop)
    window.show()

    exit_code = app.exec()
    async_thread.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
