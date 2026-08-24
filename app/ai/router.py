from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.ai.ollama_client import OllamaClient
from app.ai.prompts.system_prompts import TOOL_EXPERT_SYSTEM
from app.ai.prompts.task_templates import TOOL_SELECTION_TEMPLATE
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolScore
from app.tools.command_planner import CommandPlanner
from app.execution.models import CommandPlan
from app.logging_config import get_logger

logger = get_logger("ai.router")


class ToolSelection(BaseModel):
    tool_name: str
    reason: str = ""
    command_plan: CommandPlan | None = None
    expected_output_type: str = "text"
    parser: str = "generic"
    score: float = 0.0


class RoutingResult(BaseModel):
    selected_tools: list[ToolSelection] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    reasoning: str = ""


class CyberTaskRouter:
    def __init__(
        self,
        ollama_client: OllamaClient,
        tool_registry: ToolRegistry,
        command_planner: CommandPlanner,
    ) -> None:
        self._ollama = ollama_client
        self._registry = tool_registry
        self._planner = command_planner

    async def route(
        self,
        phase_name: str,
        phase_description: str,
        category: str,
        required_capabilities: list[str],
        target: str,
        risk_limit: str = "MEDIUM_RISK",
    ) -> RoutingResult:
        scores = self._planner.score_tools(
            required_capabilities=required_capabilities,
            input_types=[],
            output_types=[],
            risk_limit=risk_limit,
            category=category if category else None,
        )

        installed_tools = [
            s.tool_name for s in scores
            if s.installation_status > 0 and s.total_score > 10
        ]

        if not installed_tools:
            all_category_tools = self._registry.get_tools_by_category(category) if category else []
            available_tools_detail = "\n".join(
                f"- {t.name}: {t.description} (capabilities: {', '.join(t.capabilities)})"
                for t in all_category_tools
            )
        else:
            available_tools_detail = "\n".join(
                f"- {name}: {self._registry.get_tool(name).description if self._registry.get_tool(name) else 'unknown'}"
                for name in installed_tools[:10]
            )

        prompt = TOOL_SELECTION_TEMPLATE.format(
            phase_name=phase_name,
            phase_description=phase_description,
            category=category,
            required_capabilities=", ".join(required_capabilities),
            target=target,
            risk_limit=risk_limit,
            available_tools_detail=available_tools_detail,
            installed_tools=", ".join(installed_tools[:15]),
        )

        response = await self._ollama.generate(
            prompt=prompt,
            system=TOOL_EXPERT_SYSTEM,
            temperature=0.1,
        )

        result = self._parse_routing_result(response, target, scores)
        result.reasoning = response

        logger.info(
            "Routed %s: %d tools selected",
            phase_name,
            len(result.selected_tools),
        )
        return result

    def _parse_routing_result(
        self,
        response: str,
        target: str,
        scores: list[ToolScore],
    ) -> RoutingResult:
        result = RoutingResult()

        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            for tool_data in data.get("selected_tools", []):
                tool_name = tool_data.get("tool_name", "")
                tool_def = self._registry.get_tool(tool_name)

                cmd_plan = None
                if "command_plan" in tool_data and tool_data["command_plan"]:
                    cp = tool_data["command_plan"]
                    cmd_plan = CommandPlan(
                        executable=cp.get("executable", tool_name),
                        arguments=cp.get("arguments", []),
                        target=cp.get("target", target),
                        timeout=cp.get("timeout", 120),
                        explanation=cp.get("explanation", ""),
                        backend="wsl2",
                    )
                elif tool_def:
                    cmd_plan = self._planner.create_command_plan(tool_def, target)

                tool_score = next((s for s in scores if s.tool_name == tool_name), None)

                result.selected_tools.append(ToolSelection(
                    tool_name=tool_name,
                    reason=tool_data.get("reason", ""),
                    command_plan=cmd_plan,
                    expected_output_type=tool_data.get("expected_output_type", "text"),
                    parser=tool_data.get("parser", tool_def.parser if tool_def else "generic"),
                    score=tool_score.total_score if tool_score else 0.0,
                ))

            result.alternatives = data.get("alternatives", [])

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse routing JSON: %s", e)
            if scores:
                best = scores[0]
                tool_def = self._registry.get_tool(best.tool_name)
                if tool_def:
                    cmd_plan = self._planner.create_command_plan(tool_def, target)
                    result.selected_tools.append(ToolSelection(
                        tool_name=best.tool_name,
                        reason="Highest scoring tool from registry",
                        command_plan=cmd_plan,
                        score=best.total_score,
                    ))

        return result

    def _extract_json(self, text: str) -> str:
        import re
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.find("```", start)
            raw = text[start:end].strip() if end != -1 else text[start:].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.find("```", start)
            raw = text[start:end].strip() if end != -1 else text[start:].strip()
        else:
            brace_start = text.find("{")
            brace_end = text.rfind("}")
            if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                raw = text[brace_start:brace_end + 1]
            else:
                raw = text
        raw = re.sub(r',\s*([\]}])', r'\1', raw)
        return raw
    def route_deterministic(
        self,
        category: str,
        required_capabilities: list[str],
        target: str,
        risk_limit: str = "MEDIUM_RISK",
    ) -> RoutingResult:
        scores = self._planner.score_tools(
            required_capabilities=required_capabilities,
            input_types=[],
            output_types=[],
            risk_limit=risk_limit,
            category=category if category else None,
        )

        result = RoutingResult()
        for score in scores[:3]:
            if score.installation_status > 0 and score.total_score > 10:
                tool_def = self._registry.get_tool(score.tool_name)
                if tool_def:
                    cmd_plan = self._planner.create_command_plan(tool_def, target)
                    result.selected_tools.append(ToolSelection(
                        tool_name=score.tool_name,
                        reason=f"Score: {score.total_score:.1f}",
                        command_plan=cmd_plan,
                        score=score.total_score,
                    ))

        return result
