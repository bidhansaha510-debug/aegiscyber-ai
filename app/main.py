from __future__ import annotations

import asyncio
import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.config import get_config
from app.logging_config import setup_logging, get_logger
from app.database.connection import DatabaseManager
from app.database.migrations import MigrationManager
from app.security.authorization import AuthorizationManager
from app.security.audit import AuditLogger
from app.security.kill_switch import KillSwitch
from app.security.secrets import SecretsManager
from app.execution.manager import ExecutionManager
from app.execution.sandbox import ExecutionSandbox
from app.execution.subprocess_backend import SubprocessBackend
from app.execution.wsl_backend import WSLBackend
from app.execution.docker_backend import DockerBackend
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

    policy_engine = PolicyEngine(auth_manager)
    command_planner = CommandPlanner(tool_registry)
    parser_registry = ParserRegistry()

    knowledge_graph = KnowledgeGraph()
    osint_engine = OSINTEngine(knowledge_graph)

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
        "db": db,
        "auth_manager": auth_manager,
        "audit_logger": audit_logger,
        "kill_switch": kill_switch,
        "exec_manager": exec_manager,
        "tool_registry": tool_registry,
        "policy_engine": policy_engine,
        "parser_registry": parser_registry,
        "osint_engine": osint_engine,
        "ollama_client": ollama_client,
        "orchestrator": orchestrator,
    }


def main() -> None:
    setup_logging()
    logger = get_logger("main")

    loop = asyncio.new_event_loop()
    try:
        components = loop.run_until_complete(initialize_system())
    except Exception as e:
        logger.error("Failed to initialize system: %s", e)
        print(f"Initialization error: {e}")
        print("Starting in degraded mode without backend services...")
        components = {"orchestrator": None}
    finally:
        loop.close()

    app = QApplication(sys.argv)
    app.setApplicationName("AegisCyber AI")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AegisCyber")

    window = MainWindow(orchestrator=components.get("orchestrator"))
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
