from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import AsyncGenerator

from app.execution.models import CommandPlan, ExecutionStatus, ExecutionUpdate
from app.logging_config import get_logger

logger = get_logger("execution.wsl_backend")


class WSLBackend:
    BACKEND_NAME = "wsl2"

    def __init__(self, distro: str = "kali-linux", max_output_size: int = 10 * 1024 * 1024) -> None:
        self._distro = distro
        self._max_output_size = max_output_size
        self._is_available: bool | None = None

    async def check_available(self) -> bool:
        if self._is_available is not None:
            return self._is_available

        try:
            proc = await asyncio.create_subprocess_exec(
                "wsl", "--list", "--quiet",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            if proc.returncode == 0:
                output = stdout.decode("utf-16-le", errors="replace").strip()
                if not output:
                    output = stdout.decode("utf-8", errors="replace").strip()
                distros = [d.strip().lower() for d in output.split("\n") if d.strip()]
                self._is_available = self._distro.lower() in distros
            else:
                self._is_available = False
        except Exception as e:
            logger.warning("WSL check failed: %s", e)
            self._is_available = False

        logger.info("WSL2 backend (%s): %s", self._distro, "available" if self._is_available else "unavailable")
        return self._is_available

    async def check_tool_exists(self, executable: str) -> tuple[bool, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "wsl", "-d", self._distro, "--", "which", executable,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            if proc.returncode == 0:
                path = stdout.decode("utf-8", errors="replace").strip()
                return True, path
            return False, ""
        except Exception:
            return False, ""

    async def get_tool_version(self, executable: str) -> str:
        for flag in ["--version", "-v", "-V", "version"]:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "wsl", "-d", self._distro, "--", executable, flag,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
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
        if not await self.check_available():
            yield ExecutionUpdate(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                stderr_chunk=f"WSL2 distro '{self._distro}' is not available",
            )
            return

        cmd_string = command_plan.to_command_string()
        wsl_cmd = ["wsl", "-d", self._distro, "--", "bash", "-c", cmd_string]

        yield ExecutionUpdate(
            execution_id=execution_id,
            status=ExecutionStatus.RUNNING,
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *wsl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=command_plan.working_directory,
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

        except Exception as e:
            logger.error("WSL execution error: %s", e)
            yield ExecutionUpdate(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                stderr_chunk=f"WSL execution error: {str(e)}",
            )

