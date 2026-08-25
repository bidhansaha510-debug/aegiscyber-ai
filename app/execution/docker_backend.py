from __future__ import annotations

import asyncio
import os
from typing import Any, AsyncGenerator

from app.execution.models import CommandPlan, ExecutionStatus, ExecutionUpdate
from app.logging_config import get_logger

logger = get_logger("execution.docker_backend")


class DockerBackend:
    BACKEND_NAME = "docker"

    def __init__(self, image: str = "kalilinux/kali-rolling:latest", max_output_size: int = 10 * 1024 * 1024) -> None:
        self._image = image
        self._max_output_size = max_output_size
        self._is_available: bool | None = None
        self._active_containers: set[str] = set()

    async def check_available(self, force: bool = False) -> bool:
        if self._is_available is not None and not force:
            return self._is_available

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            self._is_available = proc.returncode == 0
        except Exception as e:
            logger.warning("Docker check failed: %s", e)
            self._is_available = False

        logger.info("Docker backend: %s", "available" if self._is_available else "unavailable")
        return self._is_available

    async def check_tool_exists(self, executable: str) -> tuple[bool, str]:
        if not await self.check_available():
            return False, ""

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "run", "--rm", "--entrypoint", "which", self._image, executable,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            if proc.returncode == 0:
                return True, stdout.decode("utf-8", errors="replace").strip()
            return False, ""
        except Exception:
            return False, ""

    async def get_tool_version(self, executable: str) -> str:
        if not await self.check_available():
            return "unknown"

        for flag in ["--version", "-v", "-V", "version"]:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker", "run", "--rm", "--entrypoint", executable, self._image, flag,
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
                stderr_chunk="Docker daemon is not running or not accessible",
            )
            return

        container_name = f"aegis_{execution_id}"
        self._active_containers.add(container_name)

        cmd = [
            "docker", "run",
            "--name", container_name,
            "--rm",
            "--network", "host",
            "--cap-add", "NET_RAW",
            "--cap-add", "NET_ADMIN",
            "--memory", "2g",
            "--cpus", "2",
        ]

        if command_plan.environment:
            for k, v in command_plan.environment.items():
                cmd.extend(["-e", f"{k}={v}"])

        cmd.append(self._image)
        cmd.append("bash")
        cmd.append("-c")
        cmd.append(command_plan.to_command_string())

        yield ExecutionUpdate(
            execution_id=execution_id,
            status=ExecutionStatus.RUNNING,
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_chunks: list[str] = []
            stderr_chunks: list[str] = []
            total_output = 0

            async def read_stream(stream: asyncio.StreamReader | None, chunks: list[str]) -> None:
                nonlocal total_output
                if not stream:
                    return
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace")
                    total_output += len(decoded)
                    if total_output <= self._max_output_size:
                        chunks.append(decoded)

            if command_plan.timeout and command_plan.timeout > 0:
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
            else:
                await asyncio.gather(
                    read_stream(proc.stdout, stdout_chunks),
                    read_stream(proc.stderr, stderr_chunks),
                )
                await proc.wait()

            stdout_text = "".join(stdout_chunks)
            stderr_text = "".join(stderr_chunks)
            final_status = ExecutionStatus.COMPLETED if proc.returncode == 0 else ExecutionStatus.FAILED

            yield ExecutionUpdate(
                execution_id=execution_id,
                status=final_status,
                stdout_chunk=stdout_text,
                stderr_chunk=stderr_text,
                exit_code=proc.returncode,
            )

        except Exception as e:
            logger.error("Docker execution error: %s", e)
            yield ExecutionUpdate(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                stderr_chunk=f"Docker execution error: {str(e)}",
            )
        finally:
            self._active_containers.discard(container_name)

    async def _stop_container(self, execution_id: str) -> None:
        container_name = f"aegis_{execution_id}"
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "kill", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=5)
        except Exception:
            pass

    async def cleanup(self) -> None:
        for name in list(self._active_containers):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker", "kill", name,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                pass
        self._active_containers.clear()
