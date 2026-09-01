from __future__ import annotations

from typing import Any

from app.ai.ollama_client import OllamaClient
from app.ai.prompts.system_prompts import ANALYST_SYSTEM
from app.ai.prompts.task_templates import ANALYSIS_TEMPLATE
from app.logging_config import get_logger

logger = get_logger("ai.analyst")


class Analyst:
    def __init__(self, ollama_client: OllamaClient) -> None:
        self._ollama = ollama_client

    async def analyze(
        self,
        tool_name: str,
        command: str,
        structured_results: dict[str, Any],
        raw_output: str = "",
        target: str = "",
        investigation_context: str = "",
        known_facts: str = "",
    ) -> str:
        raw_excerpt = raw_output[:3000] if raw_output else "No raw output available"

        import json
        structured_str = json.dumps(structured_results, indent=2, default=str)
        if len(structured_str) > 5000:
            structured_str = structured_str[:5000] + "\n... (truncated)"

        prompt = ANALYSIS_TEMPLATE.format(
            investigation_context=investigation_context or "General security research",
            target=target,
            tool_name=tool_name,
            command=command,
            structured_results=structured_str,
            raw_output_excerpt=raw_excerpt,
            known_facts=known_facts or "None yet",
        )

        analysis = await self._ollama.generate(
            prompt=prompt,
            system=ANALYST_SYSTEM,
            temperature=0.2,
        )

        logger.info("Analysis complete for %s output (%d chars)", tool_name, len(analysis))
        return analysis

    async def summarize_findings(
        self,
        all_findings: list[dict[str, Any]],
        target: str = "",
        system_prompt: str = "",
    ) -> str:
        findings_text = ""
        for finding in all_findings:
            findings_text += f"\nTool: {finding.get('tool', 'unknown')}\n"
            findings_text += f"Analysis: {finding.get('analysis', '')}\n"
            findings_text += "---\n"

        prompt = f"""Synthesize the following security research findings into a comprehensive summary.

TARGET: {target}

INDIVIDUAL FINDINGS:
{findings_text}

Produce a unified summary covering:
1. Key findings ordered by importance
2. Attack surface overview
3. Potential security concerns
4. Recommended next steps"""

        summary = await self._ollama.generate(
            prompt=prompt,
            system=system_prompt or ANALYST_SYSTEM,
            temperature=0.2,
        )

        return summary
