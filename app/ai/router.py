from __future__ import annotations

import json
import re
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
        all_installed = [
            t.name for t in self._registry.get_all_tools()
            if self._registry.is_installed(t.name)
        ]

        scores = self._planner.score_tools(
            required_capabilities=required_capabilities,
            input_types=[],
            output_types=[],
            risk_limit=risk_limit,
            category=category if category else None,
        )

        cat_installed = [
            s.tool_name for s in scores
            if s.installation_status > 0 and self._registry.is_installed(s.tool_name)
        ]

        available_pool = cat_installed or all_installed

        if available_pool:
            available_tools_detail = "\n".join(
                f"- {name}: {self._registry.get_tool(name).description if self._registry.get_tool(name) else ''}"
                for name in available_pool
            )
            installed_str = ", ".join(available_pool)
        else:
            all_category_tools = self._registry.get_tools_by_category(category) if category else []
            available_tools_detail = "\n".join(
                f"- {t.name}: {t.description} (capabilities: {', '.join(t.capabilities)})"
                for t in all_category_tools
            )
            installed_str = "None"

        prompt = TOOL_SELECTION_TEMPLATE.format(
            phase_name=phase_name,
            phase_description=phase_description,
            category=category or "GENERAL_RECON",
            required_capabilities=", ".join(required_capabilities),
            target=target,
            risk_limit=risk_limit,
            available_tools_detail=available_tools_detail,
            installed_tools=installed_str,
        )

        response = await self._ollama.generate(
            prompt=prompt,
            system=TOOL_EXPERT_SYSTEM,
            temperature=0.1,
        )

        result = self._parse_routing_result(response, target, scores, all_installed)
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
        all_installed: list[str] | None = None,
    ) -> RoutingResult:
        result = RoutingResult()
        installed_set = set(all_installed or [])

        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            for tool_data in data.get("selected_tools", []):
                tool_name = tool_data.get("tool_name", "")
                if installed_set and tool_name not in installed_set:
                    logger.warning("Tool %s is not installed on system, skipping", tool_name)
                    continue

                tool_def = self._registry.get_tool(tool_name)

                cmd_plan = None
                if "command_plan" in tool_data and tool_data["command_plan"]:
                    cp = tool_data["command_plan"]
                    args = list(cp.get("arguments", []))
                    calc_timeout = int(cp.get("timeout", tool_def.default_timeout if tool_def else 1800))

                    if tool_name == "nmap":
                        if any("-p-" in str(a) for a in args):
                            calc_timeout = max(calc_timeout, 1800)
                            if not any(str(a).startswith("-T") for a in args):
                                args.insert(0, "-T4")
                        else:
                            if not any(str(a).startswith("-T") for a in args):
                                args.insert(0, "-T4")
                            calc_timeout = max(calc_timeout, 600)

                    elif tool_name == "subfinder":
                        clean_args = []
                        for a in args:
                            a_str = str(a).strip()
                            if a_str in ["-quiet", "--quiet", "-q"]:
                                clean_args.append("-silent")
                            else:
                                clean_args.append(a)
                        if "-d" not in clean_args:
                            clean_args = ["-d", target] + [x for x in clean_args if x != target]
                        if "-silent" not in clean_args:
                            clean_args.append("-silent")
                        args = clean_args

                    elif tool_name == "httpx":
                        args = ["-silent" if str(a) in ["-quiet", "--quiet", "-q"] else a for a in args]

                    elif tool_name == "dnsx":
                        cmd_plan = CommandPlan(
                            executable="sh",
                            arguments=["-c", f"echo {target} | dnsx -recon -silent"],
                            target="",
                            timeout=calc_timeout,
                            explanation=f"Query DNS records for {target} via dnsx",
                            backend="wsl2",
                        )

                    elif tool_name == "dig":
                        cleaned_args = []
                        for a in args:
                            a_str = str(a).strip()
                            if a_str.startswith("@"):
                                srv = a_str[1:].lower()
                                if srv == target.lower() or srv.endswith(target.lower()) or "127.0.0.1" in srv:
                                    continue
                            cleaned_args.append(a)
                        if not any(str(a).startswith("@") for a in cleaned_args):
                            cleaned_args.insert(0, "@8.8.8.8")
                        args = cleaned_args

                    if not cmd_plan:
                        installed_info = self._registry.get_installed_info(tool_name)
                        chosen_backend = installed_info.backend if (installed_info and installed_info.is_available) else "wsl2"

                        cmd_plan = CommandPlan(
                            executable=cp.get("executable", tool_name),
                            arguments=args,
                            target=cp.get("target", target),
                            timeout=calc_timeout,
                            explanation=cp.get("explanation", ""),
                            backend=chosen_backend,
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

        if not result.selected_tools and installed_set:
            general_scores = self._planner.score_tools(
                required_capabilities=[],
                input_types=[],
                output_types=[],
                risk_limit="MEDIUM_RISK",
            )
            for score in general_scores:
                if score.tool_name in installed_set:
                    tool_def = self._registry.get_tool(score.tool_name)
                    if tool_def:
                        cmd_plan = self._planner.create_command_plan(tool_def, target)
                        result.selected_tools.append(ToolSelection(
                            tool_name=score.tool_name,
                            reason=f"Installed fallback tool ({score.tool_name})",
                            command_plan=cmd_plan,
                            score=score.total_score,
                        ))
                        break

        return result

    def _extract_json(self, text: str) -> str:
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
            if score.installation_status > 0 and score.total_score > 10 and self._registry.is_installed(score.tool_name):
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
