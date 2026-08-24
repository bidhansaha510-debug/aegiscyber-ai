from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.ai.ollama_client import OllamaClient
from app.ai.prompts.system_prompts import VERIFIER_SYSTEM
from app.ai.prompts.task_templates import VERIFICATION_TEMPLATE
from app.logging_config import get_logger

logger = get_logger("ai.verifier")


class VerifiedConclusion(BaseModel):
    conclusion: str
    supported: bool
    evidence: str = ""
    confidence: float = 0.0
    notes: str = ""


class VerificationReport(BaseModel):
    verified_conclusions: list[VerifiedConclusion] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    additional_observations: list[str] = Field(default_factory=list)
    overall_confidence: float = 0.0


class Verifier:
    def __init__(self, ollama_client: OllamaClient) -> None:
        self._ollama = ollama_client

    async def verify(
        self,
        analysis: str,
        evidence: str,
        tool_outputs: str = "",
    ) -> VerificationReport:
        prompt = VERIFICATION_TEMPLATE.format(
            analysis=analysis[:3000],
            evidence=evidence[:3000],
            tool_outputs=tool_outputs[:2000] if tool_outputs else "See evidence above",
        )

        response = await self._ollama.generate(
            prompt=prompt,
            system=VERIFIER_SYSTEM,
            temperature=0.1,
        )

        report = self._parse_report(response)
        logger.info(
            "Verification complete: %d verified, %d unsupported, confidence=%.2f",
            len(report.verified_conclusions),
            len(report.unsupported_claims),
            report.overall_confidence,
        )
        return report

    def _parse_report(self, response: str) -> VerificationReport:
        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            conclusions = []
            for vc in data.get("verified_conclusions", []):
                conclusions.append(VerifiedConclusion(
                    conclusion=vc.get("conclusion", ""),
                    supported=vc.get("supported", False),
                    evidence=vc.get("evidence", ""),
                    confidence=float(vc.get("confidence", 0.0)),
                    notes=vc.get("notes", ""),
                ))

            report = VerificationReport(
                verified_conclusions=conclusions,
                unsupported_claims=data.get("unsupported_claims", []),
                additional_observations=data.get("additional_observations", []),
            )

            if conclusions:
                supported = [c for c in conclusions if c.supported]
                if supported:
                    report.overall_confidence = sum(c.confidence for c in supported) / len(supported)

            return report

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse verification JSON: %s", e)
            return VerificationReport(
                additional_observations=[response[:500]],
                overall_confidence=0.5,
            )

    def _extract_json(self, text: str) -> str:
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return text[start:end].strip()
        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            return text[start:end].strip()
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end != -1:
            return text[brace_start:brace_end + 1]
        return text

    async def verify_command(
        self,
        executable: str,
        arguments: list[str],
        tool_exists: bool,
        tool_documentation: str = "",
    ) -> dict[str, Any]:
        checks = {
            "executable_exists": tool_exists,
            "arguments_valid": True,
            "documentation_available": bool(tool_documentation),
        }

        if not tool_exists:
            checks["arguments_valid"] = False

        return checks
