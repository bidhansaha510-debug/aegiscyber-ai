from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.tools.schemas import ToolDefinition, ToolArgument, ToolExample, OutputPattern, InstalledTool
from app.logging_config import get_logger

logger = get_logger("tools.registry")


class ToolRegistry:
    def __init__(self, registry_dir: str | Path = "tool_registry") -> None:
        self._registry_dir = Path(registry_dir)
        self._tools: dict[str, ToolDefinition] = {}
        self._installed: dict[str, dict[str, InstalledTool]] = {}

    def load_all(self) -> int:
        if not self._registry_dir.exists():
            logger.warning("Tool registry directory does not exist: %s", self._registry_dir)
            return 0

        count = 0
        for yaml_file in sorted(self._registry_dir.glob("*.yaml")):
            try:
                self._load_tool_file(yaml_file)
                count += 1
            except Exception as e:
                logger.error("Failed to load tool definition %s: %s", yaml_file.name, e)

        for yml_file in sorted(self._registry_dir.glob("*.yml")):
            try:
                self._load_tool_file(yml_file)
                count += 1
            except Exception as e:
                logger.error("Failed to load tool definition %s: %s", yml_file.name, e)

        logger.info("Loaded %d tool definitions from %s", count, self._registry_dir)
        return count

    def _load_tool_file(self, path: Path) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return

        arguments = []
        for arg_data in data.get("arguments", []):
            if isinstance(arg_data, dict):
                arguments.append(ToolArgument(**arg_data))

        examples = []
        for ex_data in data.get("examples", []):
            if isinstance(ex_data, dict):
                examples.append(ToolExample(**ex_data))

        output_patterns = []
        for pat_data in data.get("expected_output_patterns", []):
            if isinstance(pat_data, dict):
                output_patterns.append(OutputPattern(**pat_data))

        error_patterns = []
        for pat_data in data.get("error_patterns", []):
            if isinstance(pat_data, dict):
                error_patterns.append(OutputPattern(**pat_data))

        tool = ToolDefinition(
            name=data.get("name", path.stem),
            description=data.get("description", ""),
            category=data.get("category", []),
            binary=data.get("binary", data.get("name", path.stem)),
            execution_backend=data.get("execution_backend", ["wsl2"]),
            version=data.get("version", ""),
            documentation=data.get("documentation", ""),
            capabilities=data.get("capabilities", []),
            input_types=data.get("input_types", []),
            output_types=data.get("output_types", []),
            arguments=arguments,
            required_arguments=data.get("required_arguments", []),
            optional_arguments=data.get("optional_arguments", []),
            danger_level=data.get("danger_level", "LOW_RISK"),
            allowed_modes=data.get("allowed_modes", ["passive", "active"]),
            examples=examples,
            expected_output_patterns=output_patterns,
            error_patterns=error_patterns,
            parser=data.get("parser", "generic"),
            default_timeout=data.get("default_timeout", 120),
            requires_root=data.get("requires_root", False),
        )

        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def get_all_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get_tools_by_category(self, category: str) -> list[ToolDefinition]:
        return [t for t in self._tools.values() if category in t.category]

    def get_tools_by_capability(self, capability: str) -> list[ToolDefinition]:
        return [t for t in self._tools.values() if capability in t.capabilities]

    def get_tools_by_backend(self, backend: str) -> list[ToolDefinition]:
        return [t for t in self._tools.values() if backend in t.execution_backend]

    def search_tools(self, query: str) -> list[ToolDefinition]:
        query_lower = query.lower()
        results = []
        for tool in self._tools.values():
            if (
                query_lower in tool.name.lower()
                or query_lower in tool.description.lower()
                or any(query_lower in cap.lower() for cap in tool.capabilities)
                or any(query_lower in cat.lower() for cat in tool.category)
            ):
                results.append(tool)
        return results

    def set_installed(self, name: str, backend: str, installed: InstalledTool) -> None:
        if name not in self._installed:
            self._installed[name] = {}
        self._installed[name][backend] = installed

    def is_installed(self, name: str, backend: str | None = None) -> bool:
        if name not in self._installed:
            return False
        if backend:
            return backend in self._installed[name] and self._installed[name][backend].is_available
        return any(inst.is_available for inst in self._installed[name].values())

    def get_installed_info(self, name: str, backend: str | None = None) -> InstalledTool | None:
        if name not in self._installed:
            return None
        if backend:
            return self._installed[name].get(backend)
        for inst in self._installed[name].values():
            if inst.is_available:
                return inst
        return None

    def get_all_installed(self) -> list[InstalledTool]:
        result = []
        for backends in self._installed.values():
            result.extend(backends.values())
        return result

    def get_installed_tools(self) -> list[InstalledTool]:
        return self.get_all_installed()

    def get_categories(self) -> list[str]:
        categories = set()
        for tool in self._tools.values():
            categories.update(tool.category)
        return sorted(categories)

    def get_tool_count(self) -> int:
        return len(self._tools)

    def get_installed_count(self) -> int:
        return sum(
            1 for backends in self._installed.values()
            for inst in backends.values()
            if inst.is_available
        )

    def update_tool_stats(self, name: str, backend: str, success: bool, execution_time: float) -> None:
        inst = self.get_installed_info(name, backend)
        if inst:
            if success:
                inst.success_count += 1
            else:
                inst.failure_count += 1
            total = inst.success_count + inst.failure_count
            if total > 0:
                inst.avg_execution_time = (
                    (inst.avg_execution_time * (total - 1) + execution_time) / total
                )

