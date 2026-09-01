from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from app.ai.ollama_client import OllamaClient
from app.ai.prompts.system_prompts import TOOL_EXPERT_SYSTEM
from app.ai.prompts.task_templates import TOOL_SELECTION_TEMPLATE
from app.ai.json_utils import extract_json, repair_json_with_llm
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolScore
from app.tools.command_planner import CommandPlanner
from app.execution.models import CommandPlan
from app.stealth.opsec_engine import OPSECEngine
from app.stealth.signature_evader import SignatureEvader
from app.lolbin.lolbin_engine import LOLBinEngine
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
        opsec_engine: OPSECEngine | None = None,
        signature_evader: SignatureEvader | None = None,
        lolbin_engine: LOLBinEngine | None = None,
    ) -> None:
        self._ollama = ollama_client
        self._registry = tool_registry
        self._planner = command_planner
        self._opsec = opsec_engine or OPSECEngine()
        self._evader = signature_evader or SignatureEvader()
        self._lolbin = lolbin_engine or LOLBinEngine()
        self._stealth_mode: bool = False

    @property
    def stealth_mode(self) -> bool:
        return self._stealth_mode

    @stealth_mode.setter
    def stealth_mode(self, value: bool) -> None:
        self._stealth_mode = value
        self._opsec.stealth_mode = value
        logger.info("Router stealth mode: %s", "ON" if value else "OFF")

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

        result = await self._parse_routing_result(response, target, scores, all_installed)

        if self._stealth_mode:
            result = self._apply_stealth_scoring(result, target)

        logger.info(
            "Routed %s: %d tools selected%s",
            phase_name,
            len(result.selected_tools),
            " [STEALTH]" if self._stealth_mode else "",
        )
        return result

    async def _parse_routing_result(
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
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as parse_err:
                logger.warning("Routing JSON parse failed (%s); attempting LLM repair", parse_err)
                repaired = await repair_json_with_llm(self._ollama, json_str, str(parse_err))
                if not repaired:
                    raise
                data = json.loads(extract_json(repaired))

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
                    calc_timeout = 0

                    if tool_name == "nmap":
                        if not any(str(a).startswith("-T") for a in args):
                            args.insert(0, "-T4")

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

                    elif tool_name == "nikto":
                        clean_args = []
                        for a in args:
                            a_str = str(a).strip()
                            if a_str not in ["-nocheck", "-nointeractive", "-ask"]:
                                clean_args.append(a)
                        if "-host" not in clean_args and "-h" not in clean_args:
                            clean_args = ["-host", target] + [x for x in clean_args if x != target]
                        clean_args.extend(["-nocheck", "-nointeractive", "-ask", "no"])
                        args = clean_args

                    elif tool_name == "dnsx":
                        cmd_plan = CommandPlan(
                            executable="sh",
                            arguments=["-c", f"echo {target} | dnsx -recon -silent"],
                            target="",
                            timeout=0,
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
                            timeout=0,
                            explanation=cp.get("explanation", ""),
                            backend=chosen_backend,
                        )
                elif tool_def:
                    cmd_plan = self._planner.create_command_plan(tool_def, target, timeout=0)

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
                        cmd_plan = self._planner.create_command_plan(tool_def, target, timeout=0)
                        result.selected_tools.append(ToolSelection(
                            tool_name=score.tool_name,
                            reason=f"Installed fallback tool ({score.tool_name})",
                            command_plan=cmd_plan,
                            score=score.total_score,
                        ))
                        break

        return result

    def _apply_stealth_scoring(self, result: RoutingResult, target: str) -> RoutingResult:
        """Apply OPSEC scoring and evasion in stealth mode.

        - Score each tool selection for OPSEC risk
        - Apply evasion flags to reduce signatures
        - Replace high-OPSEC tools with LOLBin alternatives
        - Reorder by OPSEC score (stealthiest first)
        """
        stealth_selections: list[ToolSelection] = []

        for tool_sel in result.selected_tools:
            if not tool_sel.command_plan:
                stealth_selections.append(tool_sel)
                continue

            opsec_score = self._opsec.evaluate_command(
                tool_sel.command_plan.executable,
                tool_sel.command_plan.arguments,
                target,
            )

            if opsec_score.total_score >= 70:
                fallback = self._opsec.resolve_stealth_fallback(
                    tool_sel.command_plan.executable,
                    tool_sel.command_plan.arguments,
                    target,
                )
                if fallback:
                    alt_exec, alt_args = fallback
                    alt_score = self._opsec.evaluate_command(alt_exec, alt_args, target)
                    original_tool = tool_sel.tool_name
                    tool_sel.tool_name = alt_exec
                    tool_sel.command_plan = CommandPlan(
                        executable=alt_exec,
                        arguments=alt_args,
                        target=target,
                        timeout=tool_sel.command_plan.timeout,
                        backend="wsl2",
                        explanation=f"Stealth fallback replacing {original_tool}",
                        risk_level="LOW_RISK",
                    )
                    tool_sel.reason = (
                        f"[STEALTH] {alt_exec} fallback — replaces {original_tool} "
                        f"(OPSEC {opsec_score.total_score} → {alt_score.total_score})"
                    )
                    logger.info(
                        "STEALTH: Replaced %s (OPSEC=%d) with %s (OPSEC=%d)",
                        original_tool, opsec_score.total_score,
                        alt_exec, alt_score.total_score,
                    )
                    stealth_selections.append(tool_sel)
                    continue

            if tool_sel.command_plan and tool_sel.command_plan.executable != "bash":
                evaded_args = self._evader.apply_evasion_to_args(
                    tool_sel.tool_name,
                    tool_sel.command_plan.arguments,
                    stealth_level="careful",
                )
                tool_sel.command_plan.arguments = evaded_args

            stealth_selections.append(tool_sel)

        def _opsec_sort_key(sel: ToolSelection) -> int:
            if not sel.command_plan:
                return 50
            score = self._opsec.evaluate_command(
                sel.command_plan.executable,
                sel.command_plan.arguments,
                target,
            )
            return score.total_score

        stealth_selections.sort(key=_opsec_sort_key)
        result.selected_tools = stealth_selections
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
                    cmd_plan = self._planner.create_command_plan(tool_def, target, timeout=0)
                    result.selected_tools.append(ToolSelection(
                        tool_name=score.tool_name,
                        reason=f"Score: {score.total_score:.1f}",
                        command_plan=cmd_plan,
                        score=score.total_score,
                    ))

        return result
