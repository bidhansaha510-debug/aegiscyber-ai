from __future__ import annotations

import asyncio
import os
import signal
import sys
from typing import Any

from app.logging_config import get_logger

logger = get_logger("security.kill_switch")


class KillSwitch:
    def __init__(self) -> None:
        self._active_processes: dict[str, asyncio.subprocess.Process] = {}
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._is_engaged = False
        self._on_engage_callbacks: list[Any] = []

    @property
    def is_engaged(self) -> bool:
        return self._is_engaged

    @property
    def active_process_count(self) -> int:
        return len(self._active_processes)

    def register_process(self, execution_id: str, process: asyncio.subprocess.Process) -> None:
        self._active_processes[execution_id] = process
        logger.debug("Process registered: %s (PID: %s)", execution_id, process.pid)

    def unregister_process(self, execution_id: str) -> None:
        self._active_processes.pop(execution_id, None)
        logger.debug("Process unregistered: %s", execution_id)

    def register_task(self, task_id: str, task: asyncio.Task) -> None:
        self._active_tasks[task_id] = task

    def unregister_task(self, task_id: str) -> None:
        self._active_tasks.pop(task_id, None)

    def on_engage(self, callback: Any) -> None:
        self._on_engage_callbacks.append(callback)

    async def engage(self) -> dict[str, Any]:
        self._is_engaged = True
        logger.critical("EMERGENCY STOP ENGAGED")

        terminated = []
        failed = []

        for exec_id, process in list(self._active_processes.items()):
            try:
                if process.returncode is None:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=3.0)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
                    terminated.append(exec_id)
                    logger.info("Terminated process: %s (PID: %s)", exec_id, process.pid)
            except Exception as e:
                failed.append({"id": exec_id, "error": str(e)})
                logger.error("Failed to terminate process %s: %s", exec_id, e)

        for task_id, task in list(self._active_tasks.items()):
            try:
                if not task.done():
                    task.cancel()
                    terminated.append(f"task:{task_id}")
            except Exception as e:
                failed.append({"id": f"task:{task_id}", "error": str(e)})

        self._active_processes.clear()
        self._active_tasks.clear()

        for callback in self._on_engage_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error("Kill switch callback error: %s", e)

        result = {
            "engaged": True,
            "terminated_count": len(terminated),
            "terminated": terminated,
            "failed": failed,
        }

        logger.critical("Emergency stop complete: %d terminated, %d failed", len(terminated), len(failed))
        return result

    async def disengage(self) -> None:
        self._is_engaged = False
        logger.info("Kill switch disengaged")

    async def terminate_single(self, execution_id: str) -> bool:
        process = self._active_processes.get(execution_id)
        if not process:
            return False

        try:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            self.unregister_process(execution_id)
            logger.info("Single process terminated: %s", execution_id)
            return True
        except Exception as e:
            logger.error("Failed to terminate %s: %s", execution_id, e)
            return False

    def get_status(self) -> dict[str, Any]:
        return {
            "is_engaged": self._is_engaged,
            "active_processes": len(self._active_processes),
            "active_tasks": len(self._active_tasks),
            "process_ids": list(self._active_processes.keys()),
        }
