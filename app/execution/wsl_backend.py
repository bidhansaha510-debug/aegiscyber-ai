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

        start_time = time.monotonic()

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

            stdout_chunks: list[str] = []
            stderr_chunks: list[str] = []
            total_output = 0

            async def read_stream(stream: asyncio.StreamReader, chunks: list[str]) -> None:
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
                        read_stream(proc.stdout, stdout_chunks),
                        read_stream(proc.stderr, stderr_chunks),
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

        except Exception as e:
            logger.error("WSL execution error: %s", e)
            yield ExecutionUpdate(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                stderr_chunk=f"WSL execution error: {str(e)}",
            )
