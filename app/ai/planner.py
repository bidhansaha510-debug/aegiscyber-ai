from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.ai.ollama_client import OllamaClient
from app.ai.prompts.system_prompts import PLANNER_SYSTEM
from app.ai.prompts.task_templates import TASK_DECOMPOSITION_TEMPLATE
from app.logging_config import get_logger

logger = get_logger("ai.planner")


class TaskPhase(BaseModel):
    phase_number: int
    name: str
    description: str = ""
    category: str = ""
    required_capabilities: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    risk_level: str = "LOW_RISK"
    depends_on: list[int] = Field(default_factory=list)
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
            scope_info=scope_info or "No scope defined yet",
            available_backends=available_backends or "native, wsl2",
            available_tools=available_tools or "See tool registry",
        )

        response = await self._ollama.generate(
            prompt=prompt,
            system=PLANNER_SYSTEM,
            temperature=0.1,
        )

        plan = self._parse_plan(response)
        plan.raw_response = response
        logger.info("Task decomposed: intent=%s, phases=%d", plan.intent, len(plan.phases))
        return plan

    def _parse_plan(self, response: str) -> TaskPlan:
        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            phases = []
            for phase_data in data.get("phases", []):
                phases.append(TaskPhase(
                    phase_number=phase_data.get("phase_number", len(phases) + 1),
                    name=phase_data.get("name", ""),
                    description=phase_data.get("description", ""),
                    category=phase_data.get("category", ""),
                    required_capabilities=phase_data.get("required_capabilities", []),
                    expected_outputs=phase_data.get("expected_outputs", []),
                    risk_level=phase_data.get("risk_level", "LOW_RISK"),
                    depends_on=phase_data.get("depends_on", []),
                ))

            return TaskPlan(
                intent=data.get("intent", ""),
                target=data.get("target", ""),
                authorization_required=data.get("authorization_required", True),
                passive_only=data.get("passive_only", False),
                phases=phases,
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse plan JSON: %s", e)
            return TaskPlan(
                intent="unparsed_request",
                phases=[TaskPhase(
                    phase_number=1,
                    name="general_task",
                    description=response[:500],
                    category="UTILITY",
                )],
            )

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
