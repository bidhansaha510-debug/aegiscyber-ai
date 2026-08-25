from __future__ import annotations

import asyncio
from typing import Any

from app.execution.models import CommandPlan, ExecutionUpdate, ExecutionStatus
from app.logging_config import get_logger

logger = get_logger("execution.sandbox")


class ExecutionSandbox:
    def __init__(
        self,
        max_output_size: int = 10 * 1024 * 1024,
        default_timeout: int = 0,
        max_concurrent: int = 5,
    ) -> None:
        self._max_output_size = max_output_size
        self._default_timeout = default_timeout
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0

    @property
    def active_count(self) -> int:
        return self._active_count

    def validate_command_plan(self, plan: CommandPlan) -> tuple[bool, list[str]]:
        issues: list[str] = []

        if not plan.executable:
            issues.append("No executable specified")

        if not plan.executable.replace("-", "").replace("_", "").replace(".", "").isalnum():
            if "/" not in plan.executable and "\\" not in plan.executable:
                issues.append(f"Suspicious executable name: {plan.executable}")

        dangerous_patterns = [
            "rm -rf /",
            "mkfs",
            "> /dev/sd",
            "dd if=",
            ":(){ :|:& };:",
            "chmod -R 777 /",
            "wget|sh",
            "curl|sh",
        ]
        cmd_string = plan.to_command_string().lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in cmd_string:
                issues.append(f"Dangerous pattern detected: {pattern}")

        shell_operators = ["&&", "||", "|", ";", "`", "$("]
        for arg in plan.arguments:
            for op in shell_operators:
                if op in arg and plan.backend != "wsl2":
                    issues.append(f"Shell operator in argument: {op}")

        return len(issues) == 0, issues

    async def acquire(self) -> bool:
        acquired = self._semaphore._value > 0
        if not acquired:
            logger.warning("Maximum concurrent executions reached (%d)", self._max_concurrent)
        await self._semaphore.acquire()
        self._active_count += 1
        return True

    def release(self) -> None:
        self._active_count = max(0, self._active_count - 1)
        self._semaphore.release()

    def get_status(self) -> dict[str, Any]:
        return {
            "active_executions": self._active_count,
            "max_concurrent": self._max_concurrent,
            "available_slots": self._semaphore._value,
        }
