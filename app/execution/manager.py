from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable

from app.config import get_config
from app.execution.models import (
    CommandPlan,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionUpdate,
)
from app.execution.subprocess_backend import SubprocessBackend
from app.execution.wsl_backend import WSLBackend
from app.execution.docker_backend import DockerBackend
from app.execution.sandbox import ExecutionSandbox
from app.security.kill_switch import KillSwitch
from app.logging_config import get_logger

logger = get_logger("execution.manager")


class ExecutionManager:
    def __init__(self, kill_switch: KillSwitch | None = None) -> None:
        config = get_config()
        self._subprocess_backend = SubprocessBackend(config.execution.max_output_size_bytes)
        self._wsl_backend = WSLBackend(config.execution.wsl_distro, config.execution.max_output_size_bytes)
        self._docker_backend = DockerBackend(config.execution.docker_image, config.execution.max_output_size_bytes)
        self._sandbox = ExecutionSandbox(
            max_output_size=config.execution.max_output_size_bytes,
            default_timeout=config.execution.default_timeout,
            max_concurrent=config.execution.max_concurrent_executions,
        )
        self._kill_switch = kill_switch or KillSwitch()
        self._executions: dict[str, ExecutionResult] = {}
        self._update_callbacks: list[Callable] = []
        self._backend_availability: dict[str, bool] = {}

    async def initialize(self) -> dict[str, bool]:
        config = get_config()
        availability = {}

        availability["native"] = True

        if config.execution.enable_wsl:
            availability["wsl2"] = await self._wsl_backend.check_available()
        else:
            availability["wsl2"] = False

        if config.execution.enable_docker:
            availability["docker"] = await self._docker_backend.check_available()
        else:
            availability["docker"] = False

        self._backend_availability = availability
        logger.info("Backend availability: %s", availability)
        return availability

    def on_update(self, callback: Callable) -> None:
        self._update_callbacks.append(callback)

    def get_backend(self, backend_name: str) -> SubprocessBackend | WSLBackend | DockerBackend | None:
        backends = {
            "native": self._subprocess_backend,
            "wsl2": self._wsl_backend,
            "docker": self._docker_backend,
        }
        return backends.get(backend_name)

    def is_backend_available(self, backend_name: str) -> bool:
        return self._backend_availability.get(backend_name, False)

    def get_available_backends(self) -> list[str]:
        return [name for name, available in self._backend_availability.items() if available]

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if self._kill_switch.is_engaged:
            return ExecutionResult(
                id=request.id,
                task_id=request.task_id,
                tool_name=request.command_plan.executable,
                backend=request.command_plan.backend,
                command=request.command_plan.to_command_string(),
                status=ExecutionStatus.BLOCKED,
                error_message="Kill switch is engaged",
            )

        valid, issues = self._sandbox.validate_command_plan(request.command_plan)
        if not valid:
            return ExecutionResult(
                id=request.id,
                task_id=request.task_id,
                tool_name=request.command_plan.executable,
                backend=request.command_plan.backend,
                command=request.command_plan.to_command_string(),
                status=ExecutionStatus.BLOCKED,
                error_message=f"Sandbox validation failed: {'; '.join(issues)}",
            )

        backend = self.get_backend(request.command_plan.backend)
        if not backend:
            return ExecutionResult(
                id=request.id,
                task_id=request.task_id,
                tool_name=request.command_plan.executable,
                backend=request.command_plan.backend,
                command=request.command_plan.to_command_string(),
                status=ExecutionStatus.FAILED,
                error_message=f"Unknown backend: {request.command_plan.backend}",
            )

        if not self.is_backend_available(request.command_plan.backend):
            return ExecutionResult(
                id=request.id,
                task_id=request.task_id,
                tool_name=request.command_plan.executable,
                backend=request.command_plan.backend,
                command=request.command_plan.to_command_string(),
                status=ExecutionStatus.FAILED,
                error_message=f"Backend not available: {request.command_plan.backend}",
            )

        await self._sandbox.acquire()
        start_time = time.monotonic()
        started_at = datetime.now(timezone.utc).isoformat()

        result = ExecutionResult(
            id=request.id,
            task_id=request.task_id,
            tool_name=request.command_plan.executable,
            backend=request.command_plan.backend,
            command=request.command_plan.to_command_string(),
            status=ExecutionStatus.RUNNING,
            started_at=started_at,
        )
        self._executions[request.id] = result

        try:
            async for update in backend.execute(request.command_plan, request.id):
                result.status = update.status
                if update.stdout_chunk:
                    result.stdout = update.stdout_chunk
                if update.stderr_chunk:
                    result.stderr = update.stderr_chunk

                for callback in self._update_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(update)
                        else:
                            callback(update)
                    except Exception as e:
                        logger.error("Update callback error: %s", e)

            duration = time.monotonic() - start_time
            result.completed_at = datetime.now(timezone.utc).isoformat()
            result.duration_seconds = round(duration, 3)

        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now(timezone.utc).isoformat()
            result.duration_seconds = round(time.monotonic() - start_time, 3)
            logger.error("Execution %s failed: %s", request.id, e)
        finally:
            self._sandbox.release()

        self._executions[request.id] = result
        logger.info(
            "Execution %s completed: status=%s, duration=%.1fs",
            request.id,
            result.status.value,
            result.duration_seconds,
        )
        return result

    async def check_tool(self, tool_name: str, backend: str = "native") -> tuple[bool, str, str]:
        backend_obj = self.get_backend(backend)
        if not backend_obj:
            return False, "", "Unknown backend"

        exists, path = await backend_obj.check_tool_exists(tool_name)
        if exists:
            version = await backend_obj.get_tool_version(tool_name)
            return True, path, version
        return False, "", "Not found"

    def get_execution(self, execution_id: str) -> ExecutionResult | None:
        return self._executions.get(execution_id)

    def get_all_executions(self) -> list[ExecutionResult]:
        return list(self._executions.values())

    def get_status(self) -> dict[str, Any]:
        return {
            "backends": self._backend_availability,
            "sandbox": self._sandbox.get_status(),
            "kill_switch": self._kill_switch.get_status(),
            "total_executions": len(self._executions),
        }
