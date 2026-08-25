from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.ai.ollama_client import OllamaClient
from app.logging_config import get_logger

logger = get_logger("ai.poc_generator")

POC_SYSTEM_PROMPT = """You are a senior penetration tester writing a Proof of Concept (POC) report.
Given security tool output and analysis findings, generate a professional POC document.

The POC must contain:
1. VULNERABILITY TITLE - A clear, specific title
2. SEVERITY - Critical, High, Medium, Low, or Informational
3. AFFECTED TARGET - The exact URL, IP, host, or service affected
4. DESCRIPTION - What was found and why it matters
5. TECHNICAL DETAILS - Exact technical evidence from the scan output
6. REPRODUCTION STEPS - Numbered steps to reproduce the finding
7. PROOF COMMAND - The exact command(s) that demonstrate the vulnerability
8. IMPACT - What an attacker could achieve by exploiting this
9. REMEDIATION - Specific fix recommendations

Format the output EXACTLY as:

VULNERABILITY TITLE: <title>
SEVERITY: <Critical|High|Medium|Low|Informational>
AFFECTED TARGET: <target>

DESCRIPTION:
<description>

TECHNICAL DETAILS:
<details>

REPRODUCTION STEPS:
1. <step>
2. <step>
...

PROOF COMMAND:
<command>

IMPACT:
<impact>

REMEDIATION:
<remediation>

Be specific. Use the actual data from the scan. Never fabricate findings.
If there are multiple vulnerabilities, separate each POC with a line of dashes (---).
"""


class POCEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    title: str = ""
    severity: str = "Informational"
    target: str = ""
    description: str = ""
    technical_details: str = ""
    reproduction_steps: list[str] = Field(default_factory=list)
    proof_command: str = ""
    impact: str = ""
    remediation: str = ""
    tool_name: str = ""
    raw_output: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    investigation_id: str = ""


class POCGenerator:
    def __init__(self, ollama_client: OllamaClient) -> None:
        self._ollama = ollama_client
        self._poc_store: list[POCEntry] = []

    async def generate_poc(
        self,
        tool_name: str,
        command: str,
        raw_output: str,
        analysis: str,
        target: str,
        investigation_id: str = "",
    ) -> list[POCEntry]:
        prompt = (
            f"Tool: {tool_name}\n"
            f"Command: {command}\n"
            f"Target: {target}\n\n"
            f"Raw Output:\n{raw_output[:4000]}\n\n"
            f"Analysis:\n{analysis[:2000]}\n\n"
            f"Generate a POC for every vulnerability or security finding discovered above."
        )

        response = await self._ollama.generate(
            prompt=prompt,
            system=POC_SYSTEM_PROMPT,
            temperature=0.2,
        )

        if not response.strip():
            return []

        entries = self._parse_poc_response(response, tool_name, target, raw_output, investigation_id)
        self._poc_store.extend(entries)
        logger.info("Generated %d POC entries for %s against %s", len(entries), tool_name, target)
        return entries

    def _parse_poc_response(
        self,
        response: str,
        tool_name: str,
        target: str,
        raw_output: str,
        investigation_id: str,
    ) -> list[POCEntry]:
        entries: list[POCEntry] = []
        blocks = response.split("---")

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            entry = POCEntry(
                tool_name=tool_name,
                target=target,
                raw_output=raw_output[:2000],
                investigation_id=investigation_id,
            )

            lines = block.split("\n")
            current_section = ""
            section_buffer: list[str] = []

            for line in lines:
                stripped = line.strip()

                if stripped.startswith("VULNERABILITY TITLE:"):
                    self._flush_section(entry, current_section, section_buffer)
                    entry.title = stripped.replace("VULNERABILITY TITLE:", "").strip()
                    current_section = ""
                    section_buffer = []

                elif stripped.startswith("SEVERITY:"):
                    self._flush_section(entry, current_section, section_buffer)
                    raw_severity = stripped.replace("SEVERITY:", "").strip()
                    entry.severity = self._normalize_severity(raw_severity)
                    current_section = ""
                    section_buffer = []

                elif stripped.startswith("AFFECTED TARGET:"):
                    self._flush_section(entry, current_section, section_buffer)
                    entry.target = stripped.replace("AFFECTED TARGET:", "").strip() or target
                    current_section = ""
                    section_buffer = []

                elif stripped == "DESCRIPTION:":
                    self._flush_section(entry, current_section, section_buffer)
                    current_section = "description"
                    section_buffer = []

                elif stripped == "TECHNICAL DETAILS:":
                    self._flush_section(entry, current_section, section_buffer)
                    current_section = "technical_details"
                    section_buffer = []

                elif stripped == "REPRODUCTION STEPS:":
                    self._flush_section(entry, current_section, section_buffer)
                    current_section = "reproduction_steps"
                    section_buffer = []

                elif stripped == "PROOF COMMAND:":
                    self._flush_section(entry, current_section, section_buffer)
                    current_section = "proof_command"
                    section_buffer = []

                elif stripped == "IMPACT:":
                    self._flush_section(entry, current_section, section_buffer)
                    current_section = "impact"
                    section_buffer = []

                elif stripped == "REMEDIATION:":
                    self._flush_section(entry, current_section, section_buffer)
                    current_section = "remediation"
                    section_buffer = []

                else:
                    if current_section:
                        section_buffer.append(line)

            self._flush_section(entry, current_section, section_buffer)

            if entry.title:
                entries.append(entry)

        if not entries and response.strip():
            fallback = POCEntry(
                title=f"Security Findings from {tool_name}",
                severity="Informational",
                target=target,
                description=response[:1500],
                tool_name=tool_name,
                raw_output=raw_output[:2000],
                investigation_id=investigation_id,
            )
            entries.append(fallback)

        return entries

    def _flush_section(self, entry: POCEntry, section: str, buffer: list[str]) -> None:
        if not section or not buffer:
            return
        text = "\n".join(buffer).strip()
        if section == "description":
            entry.description = text
        elif section == "technical_details":
            entry.technical_details = text
        elif section == "reproduction_steps":
            steps = []
            for line in buffer:
                cleaned = line.strip()
                if cleaned and cleaned[0].isdigit():
                    idx = cleaned.find(".")
                    if idx != -1:
                        cleaned = cleaned[idx + 1:].strip()
                    if cleaned:
                        steps.append(cleaned)
                elif cleaned:
                    steps.append(cleaned)
            entry.reproduction_steps = steps
        elif section == "proof_command":
            entry.proof_command = text
        elif section == "impact":
            entry.impact = text
        elif section == "remediation":
            entry.remediation = text

    def _normalize_severity(self, raw: str) -> str:
        raw_lower = raw.lower().strip()
        severity_map = {
            "critical": "Critical",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "informational": "Informational",
            "info": "Informational",
        }
        return severity_map.get(raw_lower, "Informational")

    def get_all_pocs(self) -> list[POCEntry]:
        return list(self._poc_store)

    def get_pocs_by_investigation(self, investigation_id: str) -> list[POCEntry]:
        return [p for p in self._poc_store if p.investigation_id == investigation_id]

    def get_pocs_by_severity(self, severity: str) -> list[POCEntry]:
        return [p for p in self._poc_store if p.severity.lower() == severity.lower()]

    def get_poc_count(self) -> int:
        return len(self._poc_store)

    def clear(self) -> None:
        self._poc_store.clear()

    def export_pocs_markdown(self, pocs: list[POCEntry] | None = None) -> str:
        target_pocs = pocs or self._poc_store
        if not target_pocs:
            return "No POC entries found."

        sections: list[str] = []
        sections.append("# AegisCyber AI - Proof of Concept Report")
        sections.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

        for i, poc in enumerate(target_pocs, 1):
            section = []
            section.append(f"## POC #{i}: {poc.title}")
            section.append(f"**Severity:** {poc.severity}")
            section.append(f"**Target:** {poc.target}")
            section.append(f"**Tool:** {poc.tool_name}")
            section.append(f"**Date:** {poc.created_at}\n")

            if poc.description:
                section.append(f"### Description\n{poc.description}\n")

            if poc.technical_details:
                section.append(f"### Technical Details\n{poc.technical_details}\n")

            if poc.reproduction_steps:
                section.append("### Reproduction Steps")
                for j, step in enumerate(poc.reproduction_steps, 1):
                    section.append(f"{j}. {step}")
                section.append("")

            if poc.proof_command:
                section.append("### Proof Command\n```\n" + poc.proof_command + "\n```\n")

            if poc.impact:
                section.append(f"### Impact\n{poc.impact}\n")

            if poc.remediation:
                section.append(f"### Remediation\n{poc.remediation}\n")

            section.append("---\n")
            sections.append("\n".join(section))

        return "\n".join(sections)
