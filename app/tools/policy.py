from __future__ import annotations

import ipaddress
import re
from typing import Any

from app.config import get_config, RiskLevel
from app.execution.models import CommandPlan, PolicyDecision
from app.security.authorization import AuthorizationManager
from app.tools.schemas import ToolDefinition
from app.logging_config import get_logger

logger = get_logger("tools.policy")

BLOCKED_EXECUTABLES = {
    "rm", "rmdir", "mkfs", "dd", "fdisk", "parted",
    "shutdown", "reboot", "init", "systemctl",
    "useradd", "userdel", "usermod", "passwd",
    "iptables", "ip6tables", "nft",
    "mount", "umount",
}

HIGH_RISK_EXECUTABLES = {
    "metasploit", "msfconsole", "msfvenom",
    "responder", "ettercap", "bettercap",
    "aircrack-ng", "airmon-ng", "aireplay-ng",
    "john", "hashcat", "hydra",
    "sqlmap",
}

MEDIUM_RISK_EXECUTABLES = {
    "nmap", "masscan",
    "nikto", "nuclei",
    "gobuster", "ffuf", "dirb", "dirbuster",
    "enum4linux", "smbclient",
    "netcat", "nc", "ncat",
}

DANGEROUS_ARGUMENT_PATTERNS = [
    (re.compile(r"--script\s*=?\s*exploit", re.IGNORECASE), "Exploit scripts blocked"),
    (re.compile(r"-oG\s*/dev/", re.IGNORECASE), "Output to device files blocked"),
    (re.compile(r">\s*/etc/", re.IGNORECASE), "Writing to system directories blocked"),
    (re.compile(r"\brm\s+-rf\b", re.IGNORECASE), "Recursive delete blocked"),
    (re.compile(r";\s*rm\b", re.IGNORECASE), "Chained delete blocked"),
    (re.compile(r"\bwget\s.*\|\s*sh\b", re.IGNORECASE), "Pipe to shell blocked"),
    (re.compile(r"\bcurl\s.*\|\s*sh\b", re.IGNORECASE), "Pipe to shell blocked"),
    (re.compile(r"\bchmod\s+777\b", re.IGNORECASE), "World-writable permissions blocked"),
    (re.compile(r"\bchmod\s+\+s\b", re.IGNORECASE), "SUID bit modification blocked"),
]

SAFE_EXECUTABLES = {
    "dig", "nslookup", "host",
    "whois",
    "curl", "wget",
    "ping", "traceroute", "tracert",
    "openssl",
}


class PolicyEngine:
    def __init__(self, auth_manager: AuthorizationManager | None = None) -> None:
        self._auth_manager = auth_manager or AuthorizationManager()
        self._config = get_config()
        self._custom_blocked: set[str] = set()
        self._custom_allowed: set[str] = set()

    def evaluate(
        self,
        command_plan: CommandPlan,
        tool_definition: ToolDefinition | None = None,
        investigation_id: str | None = None,
    ) -> PolicyDecision:
        executable = command_plan.executable.lower().strip()
        executable_base = executable.split("/")[-1].split("\\")[-1]

        if executable_base in self._custom_blocked or executable_base in BLOCKED_EXECUTABLES:
            return PolicyDecision(
                allowed=False,
                risk=RiskLevel.BLOCKED.value,
                reason=f"Executable '{executable_base}' is blocked by policy",
            )

        issues = self._check_dangerous_arguments(command_plan)
        if issues:
            return PolicyDecision(
                allowed=False,
                risk=RiskLevel.BLOCKED.value,
                reason=f"Dangerous arguments detected: {'; '.join(issues)}",
                blocked_arguments=issues,
            )

        if command_plan.target:
            authorized, auth_reason = self._auth_manager.check_authorization(
                command_plan.target, investigation_id
            )
            if not authorized:
                return PolicyDecision(
                    allowed=False,
                    risk=RiskLevel.BLOCKED.value,
                    reason=auth_reason,
                )

        risk = self._classify_risk(command_plan, tool_definition)
        warnings = self._generate_warnings(command_plan, tool_definition)

        requires_approval = False
        allowed = True

        if risk == RiskLevel.SAFE:
            allowed = True
        elif risk == RiskLevel.LOW_RISK:
            allowed = self._config.security.auto_approve_safe or self._config.security.auto_approve_low_risk
            requires_approval = not allowed
        elif risk == RiskLevel.MEDIUM_RISK:
            requires_approval = self._config.security.require_approval_medium
            allowed = True
        elif risk == RiskLevel.HIGH_RISK:
            if self._config.security.block_high_risk:
                return PolicyDecision(
                    allowed=False,
                    risk=risk.value,
                    reason="High-risk operations are blocked by policy",
                    warnings=warnings,
                )
            requires_approval = self._config.security.require_approval_high
            allowed = True

        return PolicyDecision(
            allowed=allowed,
            risk=risk.value,
            reason=f"Command classified as {risk.value}",
            requires_approval=requires_approval,
            warnings=warnings,
        )

    def _classify_risk(self, plan: CommandPlan, tool_def: ToolDefinition | None) -> RiskLevel:
        executable_base = plan.executable.lower().split("/")[-1].split("\\")[-1]

        if executable_base in SAFE_EXECUTABLES or executable_base in self._custom_allowed:
            return RiskLevel.SAFE

        if tool_def and tool_def.danger_level:
            try:
                return RiskLevel(tool_def.danger_level)
            except ValueError:
                pass

        if executable_base in HIGH_RISK_EXECUTABLES:
            return RiskLevel.HIGH_RISK

        if executable_base in MEDIUM_RISK_EXECUTABLES:
            return RiskLevel.MEDIUM_RISK

        args_string = " ".join(plan.arguments).lower()

        aggressive_flags = ["-A", "--aggressive", "-T5", "-T4", "--script=vuln"]
        for flag in aggressive_flags:
            if flag.lower() in args_string:
                return RiskLevel.MEDIUM_RISK

        return RiskLevel.LOW_RISK

    def _check_dangerous_arguments(self, plan: CommandPlan) -> list[str]:
        full_command = plan.to_command_string()
        issues = []
        for pattern, message in DANGEROUS_ARGUMENT_PATTERNS:
            if pattern.search(full_command):
                issues.append(message)
        return issues

    def _generate_warnings(self, plan: CommandPlan, tool_def: ToolDefinition | None) -> list[str]:
        warnings = []

        if tool_def and tool_def.requires_root:
            warnings.append("This tool may require root/administrator privileges")

        args_string = " ".join(plan.arguments).lower()
        if "-p-" in args_string or "-p 1-65535" in args_string:
            warnings.append("Full port scan may take a long time and generate significant traffic")

        if any(flag in args_string for flag in ["-sv", "-sc", "-a", "--script"]):
            warnings.append("Service/script scanning generates active network traffic")

        if 0 < plan.timeout <= 600:
            warnings.append(f"Long timeout configured: {plan.timeout}s")

        return warnings

    def add_blocked_executable(self, executable: str) -> None:
        self._custom_blocked.add(executable.lower())

    def add_allowed_executable(self, executable: str) -> None:
        self._custom_allowed.add(executable.lower())

    def remove_blocked_executable(self, executable: str) -> None:
        self._custom_blocked.discard(executable.lower())

