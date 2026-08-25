from __future__ import annotations

from typing import Any

from app.execution.models import CommandPlan
from app.tools.schemas import ToolDefinition, ToolScore
from app.tools.registry import ToolRegistry
from app.logging_config import get_logger

logger = get_logger("tools.command_planner")


class CommandPlanner:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def score_tools(
        self,
        required_capabilities: list[str],
        input_types: list[str],
        output_types: list[str],
        risk_limit: str = "MEDIUM_RISK",
        category: str | None = None,
    ) -> list[ToolScore]:
        if category:
            candidates = self._registry.get_tools_by_category(category)
        else:
            candidates = self._registry.get_all_tools()

        scores: list[ToolScore] = []
        risk_order = {"SAFE": 0, "LOW_RISK": 1, "MEDIUM_RISK": 2, "HIGH_RISK": 3, "BLOCKED": 4}
        max_risk = risk_order.get(risk_limit, 2)

        for tool in candidates:
            tool_risk = risk_order.get(tool.danger_level, 1)
            if tool_risk > max_risk:
                continue

            score = ToolScore(tool_name=tool.name)

            if required_capabilities:
                matching = sum(1 for cap in required_capabilities if cap in tool.capabilities)
                score.capability_match = (matching / len(required_capabilities)) * 30

            if input_types:
                matching = sum(1 for it in input_types if it in tool.input_types)
                score.input_match = (matching / len(input_types)) * 15

            if output_types:
                matching = sum(1 for ot in output_types if ot in tool.output_types)
                score.output_match = (matching / len(output_types)) * 15

            score.reliability = 10.0

            if self._registry.is_installed(tool.name):
                score.installation_status = 20.0
                installed = self._registry.get_installed_info(tool.name)
                if installed:
                    total = installed.success_count + installed.failure_count
                    if total > 0:
                        success_rate = installed.success_count / total
                        score.historical_success = success_rate * 10.0
            else:
                score.installation_status = 0.0

            score.risk_penalty = tool_risk * 3.0
            score.calculate_total()
            scores.append(score)

        scores.sort(key=lambda s: s.total_score, reverse=True)
        return scores

    def create_command_plan(
        self,
        tool: ToolDefinition,
        target: str,
        arguments: dict[str, Any] | None = None,
        backend: str | None = None,
        timeout: int | None = None,
    ) -> CommandPlan:
        args = self._build_arguments(tool, arguments or {})

        selected_backend = backend
        if not selected_backend:
            for be in tool.execution_backend:
                installed = self._registry.get_installed_info(tool.name, be)
                if installed and installed.is_available:
                    selected_backend = be
                    break
            if not selected_backend:
                selected_backend = tool.execution_backend[0] if tool.execution_backend else "wsl2"

        return CommandPlan(
            executable=tool.binary,
            arguments=args,
            target=target,
            timeout=timeout or tool.default_timeout,
            backend=selected_backend,
            risk_level=tool.danger_level,
            explanation=f"Running {tool.name} against {target}",
        )

    def _build_arguments(self, tool: ToolDefinition, user_args: dict[str, Any]) -> list[str]:
        args: list[str] = []

        for arg_def in tool.arguments:
            if arg_def.name in user_args:
                value = user_args[arg_def.name]
                if arg_def.arg_type.value == "boolean":
                    if value:
                        args.append(arg_def.flag)
                else:
                    args.append(arg_def.flag)
                    args.append(str(value))
            elif arg_def.required and arg_def.default is not None:
                args.append(arg_def.flag)
                args.append(str(arg_def.default))

        return args

    def create_from_raw(
        self,
        executable: str,
        arguments: list[str],
        target: str,
        backend: str = "wsl2",
        timeout: int = 0,
        explanation: str = "",
    ) -> CommandPlan:
        tool = self._registry.get_tool(executable)
        risk_level = "LOW_RISK"
        if tool:
            risk_level = tool.danger_level

        return CommandPlan(
            executable=executable,
            arguments=arguments,
            target=target,
            backend=backend,
            timeout=timeout,
            risk_level=risk_level,
            explanation=explanation,
        )

