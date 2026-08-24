from __future__ import annotations

from app.database.connection import DatabaseManager
from app.logging_config import get_logger

logger = get_logger("database.migrations")

SCHEMA_VERSION = 1

MIGRATIONS = [
    {
        "version": 1,
        "description": "Initial schema",
        "sql": [
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS investigations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                target TEXT,
                scope_definition TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                investigation_id TEXT,
                intent TEXT NOT NULL,
                target TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                plan_json TEXT,
                result_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT,
                FOREIGN KEY (investigation_id) REFERENCES investigations(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                tool_name TEXT NOT NULL,
                backend TEXT NOT NULL,
                command TEXT NOT NULL,
                arguments_json TEXT,
                target TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                exit_code INTEGER,
                stdout TEXT,
                stderr TEXT,
                risk_level TEXT,
                policy_decision TEXT,
                started_at TEXT,
                completed_at TEXT,
                timeout_seconds INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                event_type TEXT NOT NULL,
                user_action TEXT,
                task_id TEXT,
                execution_id TEXT,
                tool_name TEXT,
                target TEXT,
                command TEXT,
                policy_decision TEXT,
                risk_level TEXT,
                exit_code INTEGER,
                details_json TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tool_inventory (
                name TEXT NOT NULL,
                backend TEXT NOT NULL,
                version TEXT,
                path TEXT,
                is_available INTEGER NOT NULL DEFAULT 0,
                capabilities_json TEXT,
                last_checked TEXT,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                avg_execution_time REAL,
                PRIMARY KEY (name, backend)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS osint_entities (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                source TEXT,
                first_seen TEXT NOT NULL DEFAULT (datetime('now')),
                last_seen TEXT NOT NULL DEFAULT (datetime('now')),
                metadata_json TEXT,
                investigation_id TEXT,
                FOREIGN KEY (investigation_id) REFERENCES investigations(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS osint_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_entity_id TEXT NOT NULL,
                target_entity_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                source TEXT,
                discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
                metadata_json TEXT,
                FOREIGN KEY (source_entity_id) REFERENCES osint_entities(id),
                FOREIGN KEY (target_entity_id) REFERENCES osint_entities(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS memory_conversation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS memory_investigation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                investigation_id TEXT NOT NULL,
                fact_type TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                evidence_source TEXT,
                confidence REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (investigation_id) REFERENCES investigations(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS memory_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                source TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(category, key)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_investigation ON tasks(investigation_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_executions_task ON executions(task_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_osint_entities_type ON osint_entities(entity_type)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_osint_entities_value ON osint_entities(value)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_osint_relationships_source ON osint_relationships(source_entity_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_osint_relationships_target ON osint_relationships(target_entity_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_memory_conversation_session ON memory_conversation(session_id)
            """,
        ],
    }
]


async def run_migrations(db: DatabaseManager) -> None:
    await db.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )

    row = await db.fetch_one("SELECT MAX(version) as current_version FROM schema_version")
    current_version = row["current_version"] if row and row["current_version"] else 0

    for migration in MIGRATIONS:
        if migration["version"] > current_version:
            logger.info(
                "Applying migration v%d: %s",
                migration["version"],
                migration["description"],
            )
            for sql in migration["sql"]:
                await db.execute(sql)
            await db.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (migration["version"],),
            )
            logger.info("Migration v%d applied successfully", migration["version"])

    logger.info("Database schema is up to date (v%d)", SCHEMA_VERSION)


class MigrationManager:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    async def run_migrations(self) -> None:
        await run_migrations(self.db)
