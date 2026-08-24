from __future__ import annotations

import asyncio
import time
from typing import AsyncGenerator

from app.execution.models import CommandPlan, ExecutionStatus, ExecutionUpdate
from app.logging_config import get_logger

logger = get_logger("execution.docker_backend")


class DockerBackend:
    BACKEND_NAME = "docker"

    def __init__(
        self,
        default_image: str = "kalilinux/kali-rolling",
        max_output_size: int = 10 * 1024 * 1024,
    ) -> None:
        self._default_image = default_image
        self._max_output_size = max_output_size
        self._is_available: bool | None = None

    async def check_available(self) -> bool:
        if self._is_available is not None:
            return self._is_available

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            self._is_available = proc.returncode == 0
        except Exception as e:
            logger.warning("Docker check failed: %s", e)
            self._is_available = False

        logger.info("Docker backend: %s", "available" if self._is_available else "unavailable")
        return self._is_available

    async def check_tool_exists(self, executable: str, image: str | None = None) -> tuple[bool, str]:
        image = image or self._default_image
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "run", "--rm", image, "which", executable,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
            if proc.returncode == 0:
                path = stdout.decode("utf-8", errors="replace").strip()
                return True, path
            return False, ""
        except Exception:
            return False, ""

    async def get_tool_version(self, executable: str, image: str | None = None) -> str:
        image = image or self._default_image
        for flag in ["--version", "-v", "-V"]:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker", "run", "--rm", image, executable, flag,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
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
        image: str | None = None,
    ) -> AsyncGenerator[ExecutionUpdate, None]:
        if not await self.check_available():
            yield ExecutionUpdate(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                stderr_chunk="Docker is not available",
            )
            return

        image = image or self._default_image
        cmd_string = command_plan.to_command_string()

        docker_cmd = [
            "docker", "run", "--rm",
            "--network=host",
            f"--name=aegis-{execution_id}",
            "--memory=512m",
            "--cpus=2",
            "--pids-limit=256",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        ]

        for key, value in command_plan.environment.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        docker_cmd.extend([image, "bash", "-c", cmd_string])

        yield ExecutionUpdate(
            execution_id=execution_id,
            status=ExecutionStatus.RUNNING,
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
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
                await self._stop_container(execution_id)
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=10)
                except asyncio.TimeoutError:
                    proc.kill()

                yield ExecutionUpdate(
                    execution_id=execution_id,
                    status=ExecutionStatus.TIMEOUT,
                    stdout_chunk="".join(stdout_chunks),
                    stderr_chunk=f"Docker container timed out after {command_plan.timeout}s",
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
            logger.error("Docker execution error: %s", e)
            yield ExecutionUpdate(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                stderr_chunk=f"Docker execution error: {str(e)}",
            )

    async def _stop_container(self, execution_id: str) -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "stop", f"aegis-{execution_id}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10)
        except Exception as e:
            logger.warning("Failed to stop container aegis-%s: %s", execution_id, e)
