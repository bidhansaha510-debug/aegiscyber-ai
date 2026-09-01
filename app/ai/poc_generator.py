from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.ai.ollama_client import OllamaClient
from app.ai.prompts.system_prompts import EXPLOIT_DEV_SYSTEM
from app.ai.exploit_builder import (
    build_fallback_script,
    pick_best_code,
    repair_python_code,
    strip_code_fences,
    validate_python,
)
from app.config import get_config
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
8. EXPLOIT CODE - A complete, runnable exploit script (Python source or bash) that
   exploits the finding so the reader can reproduce the impact, not just observe it
9. USAGE - The exact command line to run the exploit script
10. IMPACT - What an attacker could achieve by exploiting this
11. REMEDIATION - Specific fix recommendations

Format the output EXACTLY as:

VULNERABILITY TITLE: <title>
SEVERITY: <Critical|High|Medium|Low|Informational>
AFFECTED TARGET: <target>
EXPLOIT LANGUAGE: <python|bash>

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

EXPLOIT CODE:
<complete runnable script - no placeholders, no pseudocode, no TODOs>

USAGE:
<exact command line to run the script, e.g. python3 exploit.py <target>>

IMPACT:
<impact>

REMEDIATION:
<remediation>

Exploit code rules:
1. The script MUST be complete and runnable as-is: shebang, imports, and argparse
   that accepts an optional positional target argument which overrides the default
   target (so it can be invoked as: python3 script.py <target>)
2. PYTHON: use only the standard library (urllib.request, http.client, socket,
   subprocess, ssl, base64, sys, os)
3. BASH: plain POSIX/Kali bash with clear variables
4. Include error handling and clear SUCCESS/FAILURE output so results are verifiable
5. Demonstrate impact concretely: extract data, prove the injection, retrieve the
   sensitive resource, or verify the misconfiguration
6. Never fabricate success - if the exploit depends on an assumption, print the
   check it performs

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
    exploit_code: str = ""
    language: str = ""
    usage: str = ""
    exploit_file: str = ""
    exploitation_success: bool = False
    exploitation_result: str = ""
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
        self._weapon_mode: bool = False
        self._config = get_config()
        # Dedicated (optionally stronger) model for code generation, e.g. qwen2.5-coder.
        self._codegen_model: str = self._config.ollama.codegen_model or ""

    @property
    def weapon_mode(self) -> bool:
        return self._weapon_mode

    @weapon_mode.setter
    def weapon_mode(self, value: bool) -> None:
        self._weapon_mode = value
        logger.info("POCGenerator weapon mode: %s", "ON" if value else "OFF")

    def _exploit_dir(self, investigation_id: str) -> Path:
        base = Path(self._config.weapon.exploit_dir)
        safe_inv = re.sub(r"[^A-Za-z0-9_-]", "_", investigation_id or "unassigned")
        d = base / safe_inv
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_exploit_script(self, poc: POCEntry, investigation_id: str) -> str:
        """Write the exploit code to disk and return the file path."""
        if not poc.exploit_code.strip():
            return ""
        ext = "py" if poc.language.lower().startswith("python") else ("sh" if poc.language else "txt")
        d = self._exploit_dir(investigation_id)
        safe_title = re.sub(r"[^A-Za-z0-9_-]", "_", poc.title)[:60].strip("_") or "exploit"
        fname = f"poc_{safe_title}_{uuid.uuid4().hex[:6]}.{ext}"
        fpath = d / fname
        code = poc.exploit_code
        if fpath.suffix == ".py" and not code.startswith("#!"):
            code = "#!/usr/bin/env python3\n" + code.lstrip()
        if fpath.suffix == ".sh" and not code.startswith("#!"):
            code = "#!/bin/bash\n" + code.lstrip()
        fpath.write_text(code, encoding="utf-8", newline="\n")
        try:
            os.chmod(fpath, 0o755)
        except OSError:
            pass
        poc.exploit_file = str(fpath)
        logger.info("Exploit script saved: %s", fpath)
        return str(fpath)

    async def generate_poc(
        self,
        tool_name: str,
        command: str,
        raw_output: str,
        analysis: str,
        target: str,
        investigation_id: str = "",
    ) -> list[POCEntry]:
        if self._weapon_mode:
            system_prompt = EXPLOIT_DEV_SYSTEM
            task = (
                "Generate a complete working exploit script for every CONFIRMED, "
                "exploitable vulnerability above. Only generate EXPLOIT CODE when the "
                "evidence demonstrates exploitability. For unconfirmed findings, output "
                "the block without EXPLOIT CODE. If no exploitability exists, return nothing."
            )
        else:
            system_prompt = POC_SYSTEM_PROMPT
            task = (
                "Generate a POC for every vulnerability or security finding discovered "
                "above. Every POC MUST include a complete runnable EXPLOIT CODE section "
                "(Python source or bash) that exploits the finding against the target."
            )

        prompt = (
            f"Tool: {tool_name}\n"
            f"Command: {command}\n"
            f"Target: {target}\n\n"
            f"Raw Output:\n{raw_output[:4000]}\n\n"
            f"Analysis:\n{analysis[:2000]}\n\n"
            f"{task}"
        )

        response = await self._ollama.generate(
            prompt=prompt,
            system=system_prompt,
            temperature=0.2,
            model=self._codegen_model or None,
        )

        if not response.strip():
            return []

        entries = self._parse_poc_response(response, tool_name, target, raw_output, investigation_id)

        for poc in entries:
            await self._ensure_runnable_exploit(poc, tool_name, command, target, analysis)
            if poc.exploit_code.strip():
                self.save_exploit_script(poc, investigation_id)

        self._poc_store.extend(entries)
        mode = "exploit" if self._weapon_mode else "report"
        logger.info("Generated %d %s POC entries for %s against %s", len(entries), mode, tool_name, target)
        return entries

    async def _ensure_runnable_exploit(
        self,
        poc: POCEntry,
        tool_name: str,
        command: str,
        target: str,
        analysis: str,
    ) -> None:
        """Guarantee every POC ships runnable exploit code.

        1. Python code is statically validated (parses, stdlib-only, has a target arg).
        2. Invalid code is repaired via the LLM (with the exact validation error).
        3. If repair fails - or the model produced no code at all for an actionable
           finding - a guaranteed-runnable stdlib fallback scaffold is generated that
           re-demonstrates the finding against any target passed on the CLI.
        """
        lang = (poc.language or "").lower()

        # Detect python code that lost its language tag.
        if not lang and poc.exploit_code:
            head = poc.exploit_code.lstrip().lower()
            if head.startswith("#!/usr/bin/env python") or "import " in poc.exploit_code:
                lang = "python"
            else:
                lang = "bash"
            poc.language = lang

        if lang.startswith("python") and poc.exploit_code.strip():
            ok, err = validate_python(poc.exploit_code)
            if not ok:
                logger.info("Exploit validation failed (%s): %s", poc.title[:50], err)
                repaired = await repair_python_code(
                    self._ollama, poc.exploit_code, err,
                    poc.title or tool_name, poc.target or target,
                )
                if repaired:
                    poc.exploit_code = repaired
                    ok, err = validate_python(poc.exploit_code)
                if not ok:
                    logger.info("Exploit repair failed for '%s' - using fallback scaffold", poc.title[:50])
                    poc.exploit_code = build_fallback_script(
                        poc.title or f"{tool_name} finding",
                        poc.target or target,
                        poc.proof_command or command,
                        tool_name=tool_name,
                        description=poc.description,
                    )
                    poc.language = "python"
                    poc.usage = poc.usage or f"python3 {Path(poc.exploit_file).name if poc.exploit_file else '<script>.py'} [target]"
        elif not poc.exploit_code.strip():
            actionable = (
                poc.severity in ("Critical", "High", "Medium", "Low")
                or poc.proof_command.strip()
            )
            if actionable:
                # The model skipped the code block entirely - always give the
                # user a working exploit artifact instead of nothing.
                poc.exploit_code = build_fallback_script(
                    poc.title or f"{tool_name} finding",
                    poc.target or target,
                    poc.proof_command or command,
                    tool_name=tool_name,
                    description=poc.description or poc.technical_details,
                )
                poc.language = "python"

        if poc.exploit_code.strip() and not poc.usage:
            if poc.language.lower().startswith("python"):
                poc.usage = f"python3 <script>.py [target]  (default target: {poc.target or target})"
            else:
                poc.usage = f"bash <script>.sh [target]"

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

                elif stripped.startswith("EXPLOIT LANGUAGE:"):
                    self._flush_section(entry, current_section, section_buffer)
                    entry.language = stripped.replace("EXPLOIT LANGUAGE:", "").strip()
                    current_section = ""
                    section_buffer = []

                elif stripped == "EXPLOIT CODE:":
                    self._flush_section(entry, current_section, section_buffer)
                    current_section = "exploit_code"
                    section_buffer = []

                elif stripped == "USAGE:":
                    self._flush_section(entry, current_section, section_buffer)
                    current_section = "usage"
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
            fallback.exploit_code = pick_best_code(response) or ""
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
        elif section == "exploit_code":
            raw_lines = list(buffer)
            while raw_lines and not raw_lines[0].strip():
                raw_lines.pop(0)
            while raw_lines and not raw_lines[-1].strip():
                raw_lines.pop()
            entry.exploit_code = strip_code_fences("\n".join(raw_lines))
        elif section == "usage":
            entry.usage = text
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

            if poc.exploit_file:
                section.append(f"### Exploit Artifact\n`{poc.exploit_file}`\n")

            if poc.usage:
                section.append("### Usage\n```\n" + poc.usage + "\n```\n")

            if poc.exploit_code:
                lang = poc.language.lower() or "text"
                section.append(f"### Exploit Code ({poc.language})\n```{lang}\n" + poc.exploit_code + "\n```\n")

            if poc.exploitation_result:
                status = "SUCCESS" if poc.exploitation_success else "FAILED"
                section.append(f"### Exploitation Result: {status}\n```\n" + poc.exploitation_result + "\n```\n")

            if poc.impact:
                section.append(f"### Impact\n{poc.impact}\n")

            if poc.remediation:
                section.append(f"### Remediation\n{poc.remediation}\n")

            section.append("---\n")
            sections.append("\n".join(section))

        return "\n".join(sections)
