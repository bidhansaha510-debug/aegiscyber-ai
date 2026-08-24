from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.execution.manager import ExecutionManager
from app.tools.registry import ToolRegistry
from app.tools.schemas import InstalledTool, ToolDefinition
from app.logging_config import get_logger

logger = get_logger("tools.discovery")


class ToolDiscovery:
    def __init__(self, registry: ToolRegistry, execution_manager: ExecutionManager) -> None:
        self._registry = registry
        self._exec_manager = execution_manager
        self._scan_results: list[dict[str, Any]] = []

    async def scan_all_tools(self, backends: list[str] | None = None) -> list[dict[str, Any]]:
        if backends is None:
            backends = self._exec_manager.get_available_backends()

        all_tools = self._registry.get_all_tools()
        self._scan_results = []

        logger.info("Starting tool discovery: %d tools across %d backends", len(all_tools), len(backends))

        tasks = []
        for tool in all_tools:
            for backend in backends:
                if backend in tool.execution_backend:
                    tasks.append(self._check_single_tool(tool, backend))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, dict):
                self._scan_results.append(result)
            elif isinstance(result, Exception):
                logger.error("Tool discovery error: %s", result)

        available_count = sum(1 for r in self._scan_results if r.get("available"))
        logger.info(
            "Tool discovery complete: %d/%d available",
            available_count,
            len(self._scan_results),
        )

        return self._scan_results

    async def _check_single_tool(self, tool: ToolDefinition, backend: str) -> dict[str, Any]:
        result = {
            "name": tool.name,
            "binary": tool.binary,
            "backend": backend,
            "available": False,
            "version": "",
            "path": "",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            exists, path, version = await self._exec_manager.check_tool(tool.binary, backend)
            result["available"] = exists
            result["path"] = path
            result["version"] = version if exists else ""

            installed = InstalledTool(
                name=tool.name,
                backend=backend,
                version=version if exists else "",
                path=path,
                is_available=exists,
                last_checked=result["checked_at"],
            )
            self._registry.set_installed(tool.name, backend, installed)

            status = "✓" if exists else "✗"
            logger.debug("[%s] %s (%s): %s", status, tool.name, backend, version if exists else "not found")

        except Exception as e:
            logger.error("Error checking %s on %s: %s", tool.name, backend, e)

        return result

    async def scan_single_tool(self, tool_name: str, backend: str | None = None) -> dict[str, Any] | None:
        tool = self._registry.get_tool(tool_name)
        if not tool:
            return None

        if backend:
            return await self._check_single_tool(tool, backend)

        for be in tool.execution_backend:
            if self._exec_manager.is_backend_available(be):
                result = await self._check_single_tool(tool, be)
                if result.get("available"):
                    return result
        return None

    async def scan_category(self, category: str) -> list[dict[str, Any]]:
        tools = self._registry.get_tools_by_category(category)
        backends = self._exec_manager.get_available_backends()
        results = []

        for tool in tools:
            for backend in backends:
                if backend in tool.execution_backend:
                    result = await self._check_single_tool(tool, backend)
                    results.append(result)

        return results

    def get_scan_results(self) -> list[dict[str, Any]]:
        return self._scan_results

    def get_available_tools(self) -> list[str]:
        return [r["name"] for r in self._scan_results if r.get("available")]

    def get_discovery_summary(self) -> dict[str, Any]:
        total = len(self._scan_results)
        available = sum(1 for r in self._scan_results if r.get("available"))
        by_backend: dict[str, int] = {}
        for r in self._scan_results:
            if r.get("available"):
                be = r.get("backend", "unknown")
                by_backend[be] = by_backend.get(be, 0) + 1

        return {
            "total_checked": total,
            "available": available,
            "unavailable": total - available,
            "by_backend": by_backend,
        }
