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
        start_time = time.monotonic()
        started_at = datetime.now(timezone.utc).isoformat()

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

            stdout_chunks: list[str] = []
            stderr_chunks: list[str] = []
            total_output = 0

            async def read_stream(stream: asyncio.StreamReader, chunks: list[str], is_stderr: bool) -> None:
                nonlocal total_output
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace")
                    total_output += len(decoded)
                    if total_output <= self._max_output_size:
                        chunks.append(decoded)

            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(proc.stdout, stdout_chunks, False),
                        read_stream(proc.stderr, stderr_chunks, True),
                    ),
                    timeout=command_plan.timeout,
                )
                await proc.wait()
            except asyncio.TimeoutError:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()

                yield ExecutionUpdate(
                    execution_id=execution_id,
                    status=ExecutionStatus.TIMEOUT,
                    stdout_chunk="".join(stdout_chunks),
                    stderr_chunk=f"Process timed out after {command_plan.timeout}s",
                )
                return

            duration = time.monotonic() - start_time
            stdout_text = "".join(stdout_chunks)
            stderr_text = "".join(stderr_chunks)

            final_status = ExecutionStatus.COMPLETED if proc.returncode == 0 else ExecutionStatus.FAILED

            yield ExecutionUpdate(
                execution_id=execution_id,
                status=final_status,
                stdout_chunk=stdout_text,
                stderr_chunk=stderr_text,
                progress=1.0,
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
