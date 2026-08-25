from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from app.ai.ollama_client import OllamaClient
from app.ai.prompts.system_prompts import PLANNER_SYSTEM
from app.ai.prompts.task_templates import TASK_DECOMPOSITION_TEMPLATE
from app.logging_config import get_logger

logger = get_logger("ai.planner")


class TaskPhase(BaseModel):
    phase_number: int | str = 1
    name: str = ""
    description: str = ""
    category: str = ""
    required_capabilities: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    risk_level: str = "LOW_RISK"
    depends_on: list[Any] = Field(default_factory=list)
    status: str = "pending"
    results: dict[str, Any] = Field(default_factory=dict)


class TaskPlan(BaseModel):
    intent: str = ""
    target: str = ""
    authorization_required: bool = True
    passive_only: bool = False
    operation_mode: str = "standard"
    phases: list[TaskPhase] = Field(default_factory=list)
    raw_response: str = ""


class Planner:
    def __init__(self, ollama_client: OllamaClient) -> None:
        self._ollama = ollama_client
        self._stealth_mode: bool = False

    @property
    def stealth_mode(self) -> bool:
        return self._stealth_mode

    @stealth_mode.setter
    def stealth_mode(self, value: bool) -> None:
        self._stealth_mode = value
        logger.info("Planner stealth mode: %s", "ON" if value else "OFF")

    async def plan_task(
        self,
        user_request: str,
        context_summary: str = "",
        scope_constraints: str = "",
        available_backends: str = "",
        available_tools: str = "",
    ) -> TaskPlan:
        return await self.decompose(
            user_request=user_request,
            scope_info=scope_constraints or context_summary,
            available_backends=available_backends,
            available_tools=available_tools,
        )

    async def plan(
        self,
        user_request: str,
        scope_info: str = "",
        available_backends: str = "",
        available_tools: str = "",
    ) -> TaskPlan:
        return await self.decompose(
            user_request=user_request,
            scope_info=scope_info,
            available_backends=available_backends,
            available_tools=available_tools,
        )

    async def decompose(
        self,
        user_request: str,
        scope_info: str = "",
        available_backends: str = "",
        available_tools: str = "",
    ) -> TaskPlan:
        prompt = TASK_DECOMPOSITION_TEMPLATE.format(
            user_request=user_request,
            scope_info=scope_info or "No explicit scope defined",
            available_backends=available_backends or "native, wsl2",
            available_tools=available_tools or "nmap, dig, whois, curl",
        )

        response = await self._ollama.generate(
            prompt=prompt,
            system=PLANNER_SYSTEM,
            temperature=0.1,
        )

        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            raw_phases = data.get("phases", [])
            phases: list[TaskPhase] = []
            for i, phase_data in enumerate(raw_phases, 1):
                raw_depends = phase_data.get("depends_on", [])
                cleaned_depends = []
                for d in raw_depends:
                    if isinstance(d, int):
                        cleaned_depends.append(d)
                    elif isinstance(d, str):
                        match = re.search(r'\d+', d)
                        if match:
                            cleaned_depends.append(int(match.group(0)))
                        else:
                            cleaned_depends.append(d)
                    else:
                        cleaned_depends.append(d)

                phases.append(TaskPhase(
                    phase_number=phase_data.get("phase_number", i),
                    name=str(phase_data.get("name", f"Phase {i}")),
                    description=str(phase_data.get("description", "")),
                    category=str(phase_data.get("category", "NETWORK_RECON")),
                    required_capabilities=list(phase_data.get("required_capabilities", [])),
                    expected_outputs=list(phase_data.get("expected_outputs", [])),
                    risk_level=str(phase_data.get("risk_level", "LOW_RISK")),
                    depends_on=cleaned_depends,
                ))

            if not phases:
                phases = [TaskPhase(
                    phase_number=1,
                    name="Security Reconnaissance",
                    description="Perform security reconnaissance on target",
                    category="NETWORK_RECON",
                )]

            operation_mode = "stealth" if self._stealth_mode else "standard"
            if self._stealth_mode:
                phases = self._apply_stealth_transforms(phases)

            return TaskPlan(
                intent=str(data.get("intent", "security_investigation")),
                target=str(data.get("target", "")),
                authorization_required=bool(data.get("authorization_required", True)),
                passive_only=bool(data.get("passive_only", False)),
                operation_mode=operation_mode,
                phases=phases,
                raw_response=response,
            )
        except Exception as e:
            logger.warning("Failed to parse plan JSON: %s", e)
            return TaskPlan(
                intent="security_investigation",
                operation_mode="stealth" if self._stealth_mode else "standard",
                phases=[TaskPhase(
                    phase_number=1,
                    name="Security Reconnaissance",
                    description=response[:500] if response else "General reconnaissance",
                    category="NETWORK_RECON",
                )],
                raw_response=response,
            )

    def _apply_stealth_transforms(self, phases: list[TaskPhase]) -> list[TaskPhase]:
        """Transform a standard plan into a stealth-optimized plan.

        - Reorders phases to prioritize passive techniques
        - Lowers risk levels to avoid triggering noisy scans
        - Adds 'OPSEC cooldown' phases between active operations
        - Tags phases for LOLBin preference
        """
        stealth_phases: list[TaskPhase] = []
        phase_num = 1

        passive = [p for p in phases if p.risk_level in ("SAFE", "LOW_RISK")]
        active = [p for p in phases if p.risk_level not in ("SAFE", "LOW_RISK")]

        for p in passive:
            p.phase_number = phase_num
            p.description = f"[STEALTH] {p.description}"
            stealth_phases.append(p)
            phase_num += 1

        for p in active:
            cooldown = TaskPhase(
                phase_number=phase_num,
                name="OPSEC Cooldown",
                description="Jitter delay between active operations to avoid traffic correlation",
                category="STEALTH_SCANNING",
                required_capabilities=["timing_evasion"],
                risk_level="SAFE",
                depends_on=[phase_num - 1] if phase_num > 1 else [],
            )
            stealth_phases.append(cooldown)
            phase_num += 1

            if p.risk_level == "HIGH_RISK":
                p.risk_level = "MEDIUM_RISK"
            p.phase_number = phase_num
            p.description = f"[STEALTH/LOW-AND-SLOW] {p.description}"
            p.required_capabilities.append("stealth_alternative")
            stealth_phases.append(p)
            phase_num += 1

        logger.info(
            "Stealth transforms applied: %d phases → %d phases (added %d cooldowns)",
            len(phases), len(stealth_phases), len(stealth_phases) - len(phases),
        )
        return stealth_phases

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
