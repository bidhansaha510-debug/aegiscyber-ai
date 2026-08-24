from __future__ import annotations

import orjson
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.logging_config import get_logger

logger = get_logger("security.audit")


class AuditEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str
    user_action: str = ""
    task_id: str = ""
    execution_id: str = ""
    tool_name: str = ""
    target: str = ""
    command: str = ""
    policy_decision: str = ""
    risk_level: str = ""
    exit_code: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class AuditLogger:
    def __init__(self, log_path: str | Path = "logs/audit.jsonl", max_size_mb: int = 100) -> None:
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._max_size = max_size_mb * 1024 * 1024
        self._event_count = 0
        self._db = None

    def set_database(self, db: Any) -> None:
        self._db = db

    def log_event(self, event: AuditEvent) -> None:
        self._write_to_file(event)
        self._event_count += 1
        logger.debug("Audit event: %s", event.event_type)

    async def log_event_async(self, event: AuditEvent) -> None:
        self._write_to_file(event)
        if self._db:
            await self._persist_to_db(event)
        self._event_count += 1

    def log_user_action(self, action: str, details: dict[str, Any] | None = None) -> None:
        self.log_event(AuditEvent(
            event_type="user_action",
            user_action=action,
            details=details or {},
        ))

    def log_command_execution(
        self,
        task_id: str,
        execution_id: str,
        tool_name: str,
        target: str,
        command: str,
        policy_decision: str,
        risk_level: str,
    ) -> None:
        self.log_event(AuditEvent(
            event_type="command_execution",
            task_id=task_id,
            execution_id=execution_id,
            tool_name=tool_name,
            target=target,
            command=command,
            policy_decision=policy_decision,
            risk_level=risk_level,
        ))

    def log_execution_complete(
        self,
        execution_id: str,
        exit_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.log_event(AuditEvent(
            event_type="execution_complete",
            execution_id=execution_id,
            exit_code=exit_code,
            details=details or {},
        ))

    def log_policy_block(
        self,
        tool_name: str,
        command: str,
        reason: str,
        risk_level: str,
    ) -> None:
        self.log_event(AuditEvent(
            event_type="policy_block",
            tool_name=tool_name,
            command=command,
            policy_decision="BLOCKED",
            risk_level=risk_level,
            details={"reason": reason},
        ))

    def log_kill_switch(self, details: dict[str, Any] | None = None) -> None:
        self.log_event(AuditEvent(
            event_type="emergency_stop",
            user_action="kill_switch_activated",
            details=details or {},
        ))

    def log_scope_change(self, action: str, target: str, details: dict[str, Any] | None = None) -> None:
        self.log_event(AuditEvent(
            event_type="scope_change",
            user_action=action,
            target=target,
            details=details or {},
        ))

    def _write_to_file(self, event: AuditEvent) -> None:
        try:
            if self._log_path.exists() and self._log_path.stat().st_size > self._max_size:
                self._rotate_log()
            with open(self._log_path, "ab") as f:
                f.write(orjson.dumps(event.model_dump()) + b"\n")
        except Exception as e:
            logger.error("Failed to write audit event: %s", e)

    def _rotate_log(self) -> None:
        backup_path = self._log_path.with_suffix(
            f".{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        self._log_path.rename(backup_path)
        logger.info("Audit log rotated to %s", backup_path)

    async def _persist_to_db(self, event: AuditEvent) -> None:
        try:
            await self._db.execute(
                """INSERT INTO audit_events 
                (event_type, user_action, task_id, execution_id, tool_name, 
                 target, command, policy_decision, risk_level, exit_code, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.event_type,
                    event.user_action,
                    event.task_id,
                    event.execution_id,
                    event.tool_name,
                    event.target,
                    event.command,
                    event.policy_decision,
                    event.risk_level,
                    event.exit_code,
                    orjson.dumps(event.details).decode("utf-8"),
                ),
            )
        except Exception as e:
            logger.error("Failed to persist audit event to DB: %s", e)

    def get_event_count(self) -> int:
        return self._event_count

    def read_recent_events(self, count: int = 100) -> list[dict[str, Any]]:
        if not self._log_path.exists():
            return []
        try:
            with open(self._log_path, "rb") as f:
                lines = f.readlines()
            events = []
            for line in lines[-count:]:
                events.append(orjson.loads(line))
            return events
        except Exception as e:
            logger.error("Failed to read audit events: %s", e)
            return []
