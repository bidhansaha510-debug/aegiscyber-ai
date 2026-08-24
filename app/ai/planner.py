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
    phases: list[TaskPhase] = Field(default_factory=list)
    raw_response: str = ""


class Planner:
    def __init__(self, ollama_client: OllamaClient) -> None:
        self._ollama = ollama_client

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

        plan = self._parse_plan(response)
        plan.raw_response = response
        logger.info(
            "Task decomposed: intent=%s, phases=%d",
            plan.intent,
            len(plan.phases),
        )
        return plan

    def _parse_plan(self, response: str) -> TaskPlan:
        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            phases = []
            for i, phase_data in enumerate(data.get("phases", [])):
                raw_depends = phase_data.get("depends_on", [])
                if isinstance(raw_depends, (int, str)):
                    raw_depends = [raw_depends]
                elif not isinstance(raw_depends, list):
                    raw_depends = []

                cleaned_depends = []
                for d in raw_depends:
                    if isinstance(d, int):
                        cleaned_depends.append(d)
                    elif isinstance(d, str):
                        digits = re.findall(r'\d+', d)
                        if digits:
                            cleaned_depends.append(int(digits[0]))

                raw_num = phase_data.get("phase_number", i + 1)
                if isinstance(raw_num, str):
                    digits = re.findall(r'\d+', raw_num)
                    phase_num = int(digits[0]) if digits else i + 1
                else:
                    phase_num = int(raw_num) if raw_num else i + 1

                phases.append(TaskPhase(
                    phase_number=phase_num,
                    name=str(phase_data.get("name", f"Phase {phase_num}")),
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

            return TaskPlan(
                intent=str(data.get("intent", "security_investigation")),
                target=str(data.get("target", "")),
                authorization_required=bool(data.get("authorization_required", True)),
                passive_only=bool(data.get("passive_only", False)),
                phases=phases,
                raw_response=response,
            )
        except Exception as e:
            logger.warning("Failed to parse plan JSON: %s", e)
            return TaskPlan(
                intent="security_investigation",
                phases=[TaskPhase(
                    phase_number=1,
                    name="Security Reconnaissance",
                    description=response[:500] if response else "General reconnaissance",
                    category="NETWORK_RECON",
                )],
                raw_response=response,
            )

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
