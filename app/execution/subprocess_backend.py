from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from app.execution.models import CommandPlan, ExecutionResult, ExecutionStatus, ExecutionUpdate
from app.logging_config import get_logger

logger = get_logger("execution.subprocess_backend")


class SubprocessBackend:
    BACKEND_NAME = "native"

    def __init__(self, max_output_size: int = 10 * 1024 * 1024) -> None:
        self._max_output_size = max_output_size

    async def check_available(self) -> bool:
        return True

    async def check_tool_exists(self, executable: str) -> tuple[bool, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "where", executable,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode == 0:
                path = stdout.decode("utf-8", errors="replace").strip().split("\n")[0]
                return True, path.strip()
            return False, ""
        except Exception:
            return False, ""

    async def get_tool_version(self, executable: str) -> str:
        for flag in ["--version", "-v", "-V", "version"]:
            try:
                proc = await asyncio.create_subprocess_exec(
                    executable, flag,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
                output = (stdout or stderr).decode("utf-8", errors="replace").strip()
                if output and proc.returncode == 0:
                    return output.split("\n")[0][:200]
            except Exception:
                continue
        return "unknown"

    async def execute(
        self,
        command_plan: CommandPlan,
        execution_id: str,
    ) -> AsyncGenerator[ExecutionUpdate, None]:
        cmd = command_plan.to_command_list()

        yield ExecutionUpdate(
            execution_id=execution_id,
            status=ExecutionStatus.RUNNING,
        )

        try:
            env = None
            if command_plan.environment:
                import os
                env = {**os.environ, **command_plan.environment}

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=command_plan.working_directory,
                env=env,
            )

            queue: asyncio.Queue[tuple[bool, str] | None] = asyncio.Queue()
            active_readers = 2

            async def read_stream(stream: asyncio.StreamReader | None, is_stderr: bool) -> None:
                nonlocal active_readers
                if stream:
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        decoded = line.decode("utf-8", errors="replace")
                        await queue.put((is_stderr, decoded))
                active_readers -= 1
                if active_readers == 0:
                    await queue.put(None)

            asyncio.create_task(read_stream(proc.stdout, False))
            asyncio.create_task(read_stream(proc.stderr, True))

            stdout_chunks: list[str] = []
            stderr_chunks: list[str] = []

            while True:
                item = await queue.get()

                if item is None:
                    break

                is_stderr, chunk = item
                if is_stderr:
                    stderr_chunks.append(chunk)
                    yield ExecutionUpdate(
                        execution_id=execution_id,
                        status=ExecutionStatus.RUNNING,
                        stderr_chunk=chunk,
                    )
                else:
                    stdout_chunks.append(chunk)
                    yield ExecutionUpdate(
                        execution_id=execution_id,
                        status=ExecutionStatus.RUNNING,
                        stdout_chunk=chunk,
                    )

            await proc.wait()
            final_status = ExecutionStatus.COMPLETED if proc.returncode == 0 else ExecutionStatus.FAILED
            yield ExecutionUpdate(
                execution_id=execution_id,
                status=final_status,
                stdout_chunk="".join(stdout_chunks),
                stderr_chunk="".join(stderr_chunks),
                exit_code=proc.returncode,
            )

        except FileNotFoundError:
            yield ExecutionUpdate(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                stderr_chunk=f"Executable not found: {cmd[0]}",
            )
        except PermissionError:
            yield ExecutionUpdate(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                stderr_chunk=f"Permission denied: {cmd[0]}",
            )
        except Exception as e:
            logger.error("Subprocess execution error: %s", e)
            yield ExecutionUpdate(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                stderr_chunk=f"Execution error: {str(e)}",
            )

    def get_process(self) -> asyncio.subprocess.Process | None:
        return None

