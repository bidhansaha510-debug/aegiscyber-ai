from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class CommandPlan(BaseModel):
    executable: str
    arguments: list[str] = Field(default_factory=list)
    target: str = ""
    working_directory: str | None = None
    timeout: int = 120
    environment: dict[str, str] = Field(default_factory=dict)
    explanation: str = ""
    backend: str = "wsl2"
    risk_level: str = "LOW_RISK"

    def to_command_string(self) -> str:
        parts = [self.executable]
        target_clean = self.target.strip().lower() if self.target else ""
        seen_target = False
        for arg in self.arguments:
            if target_clean and arg.strip().lower() == target_clean:
                seen_target = True
            parts.append(arg)
        if self.target and not seen_target:
            parts.append(self.target.strip())
        return " ".join(parts)

    def to_command_list(self) -> list[str]:
        parts = [self.executable]
        target_clean = self.target.strip().lower() if self.target else ""
        seen_target = False
        for arg in self.arguments:
            if target_clean and arg.strip().lower() == target_clean:
                seen_target = True
            parts.append(arg)
        if self.target and not seen_target:
            parts.append(self.target.strip())
        return parts


class ExecutionRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    task_id: str = ""
    command_plan: CommandPlan
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExecutionResult(BaseModel):
    id: str
    task_id: str = ""
    tool_name: str
    backend: str
    command: str
    status: ExecutionStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    output_truncated: bool = False
    parsed_output: dict[str, Any] | None = None
    error_message: str = ""


class ExecutionUpdate(BaseModel):
    execution_id: str
    status: ExecutionStatus
    stdout_chunk: str = ""
    stderr_chunk: str = ""
    exit_code: int | None = None
    percentage: float = 0.0
    message: str = ""


class PolicyDecision(BaseModel):
    allowed: bool = True
    risk: str = "LOW_RISK"
    requires_approval: bool = False
    reason: str = ""
    warnings: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)
