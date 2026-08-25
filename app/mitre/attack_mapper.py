"""ATT&CK Mapper — maps tools, techniques, and findings to MITRE ATT&CK.

Automatically tags every tool execution and scan result with the
corresponding ATT&CK tactic/technique IDs and tracks kill-chain
coverage across an investigation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.logging_config import get_logger

logger = get_logger("mitre.mapper")


class KillChainPhase(BaseModel):
    """A phase in the MITRE ATT&CK kill chain."""
    tactic_id: str
    tactic_name: str
    techniques_planned: list[str] = Field(default_factory=list)
    techniques_executed: list[str] = Field(default_factory=list)
    techniques_completed: list[str] = Field(default_factory=list)
    techniques_blocked: list[str] = Field(default_factory=list)
    coverage_pct: float = 0.0


class TechniqueMapping(BaseModel):
    """Maps a tool/action to MITRE ATT&CK techniques."""
    tool_name: str
    tactic: str
    tactic_id: str
    technique_id: str
    technique_name: str
    sub_technique_id: str = ""
    sub_technique_name: str = ""
    confidence: float = 0.9
    notes: str = ""


TACTICS: dict[str, dict[str, str]] = {
    "TA0043": {"name": "Reconnaissance",           "short": "recon"},
    "TA0042": {"name": "Resource Development",      "short": "resource_dev"},
    "TA0001": {"name": "Initial Access",            "short": "initial_access"},
    "TA0002": {"name": "Execution",                 "short": "execution"},
    "TA0003": {"name": "Persistence",               "short": "persistence"},
    "TA0004": {"name": "Privilege Escalation",      "short": "privesc"},
    "TA0005": {"name": "Defense Evasion",           "short": "defense_evasion"},
    "TA0006": {"name": "Credential Access",         "short": "cred_access"},
    "TA0007": {"name": "Discovery",                 "short": "discovery"},
    "TA0008": {"name": "Lateral Movement",          "short": "lateral_movement"},
    "TA0009": {"name": "Collection",                "short": "collection"},
    "TA0011": {"name": "Command and Control",       "short": "c2"},
    "TA0010": {"name": "Exfiltration",              "short": "exfiltration"},
    "TA0040": {"name": "Impact",                    "short": "impact"},
}


TOOL_TECHNIQUE_MAP: dict[str, list[dict[str, str]]] = {
    "nmap": [
        {"tactic_id": "TA0043", "technique_id": "T1046",    "technique_name": "Network Service Discovery"},
        {"tactic_id": "TA0043", "technique_id": "T1595.001","technique_name": "Active Scanning: Scanning IP Blocks"},
        {"tactic_id": "TA0043", "technique_id": "T1595.002","technique_name": "Active Scanning: Vulnerability Scanning"},
        {"tactic_id": "TA0007", "technique_id": "T1046",    "technique_name": "Network Service Discovery"},
    ],
    "masscan": [
        {"tactic_id": "TA0043", "technique_id": "T1595.001","technique_name": "Active Scanning: Scanning IP Blocks"},
        {"tactic_id": "TA0007", "technique_id": "T1046",    "technique_name": "Network Service Discovery"},
    ],

    "nikto": [
        {"tactic_id": "TA0043", "technique_id": "T1595.002","technique_name": "Active Scanning: Vulnerability Scanning"},
        {"tactic_id": "TA0043", "technique_id": "T1592.002","technique_name": "Gather Victim Host Info: Software"},
    ],
    "gobuster": [
        {"tactic_id": "TA0043", "technique_id": "T1595.003","technique_name": "Active Scanning: Wordlist Scanning"},
        {"tactic_id": "TA0007", "technique_id": "T1083",    "technique_name": "File and Directory Discovery"},
    ],
    "ffuf": [
        {"tactic_id": "TA0043", "technique_id": "T1595.003","technique_name": "Active Scanning: Wordlist Scanning"},
        {"tactic_id": "TA0007", "technique_id": "T1083",    "technique_name": "File and Directory Discovery"},
    ],
    "nuclei": [
        {"tactic_id": "TA0043", "technique_id": "T1595.002","technique_name": "Active Scanning: Vulnerability Scanning"},
    ],

    "sqlmap": [
        {"tactic_id": "TA0001", "technique_id": "T1190",    "technique_name": "Exploit Public-Facing Application"},
        {"tactic_id": "TA0043", "technique_id": "T1595.002","technique_name": "Active Scanning: Vulnerability Scanning"},
    ],

    "dig": [
        {"tactic_id": "TA0043", "technique_id": "T1596.001","technique_name": "Search Open Technical Databases: DNS/Passive DNS"},
    ],
    "dnsx": [
        {"tactic_id": "TA0043", "technique_id": "T1596.001","technique_name": "Search Open Technical Databases: DNS/Passive DNS"},
    ],
    "whois": [
        {"tactic_id": "TA0043", "technique_id": "T1596.002","technique_name": "Search Open Technical Databases: WHOIS"},
    ],
    "subfinder": [
        {"tactic_id": "TA0043", "technique_id": "T1596.001","technique_name": "Search Open Technical Databases: DNS/Passive DNS"},
        {"tactic_id": "TA0043", "technique_id": "T1593",    "technique_name": "Search Open Websites/Domains"},
    ],
    "amass": [
        {"tactic_id": "TA0043", "technique_id": "T1596.001","technique_name": "Search Open Technical Databases: DNS/Passive DNS"},
        {"tactic_id": "TA0043", "technique_id": "T1593",    "technique_name": "Search Open Websites/Domains"},
    ],

    "httpx": [
        {"tactic_id": "TA0043", "technique_id": "T1592.002","technique_name": "Gather Victim Host Info: Software"},
        {"tactic_id": "TA0043", "technique_id": "T1595.002","technique_name": "Active Scanning: Vulnerability Scanning"},
    ],

    "hydra": [
        {"tactic_id": "TA0006", "technique_id": "T1110.001","technique_name": "Brute Force: Password Guessing"},
        {"tactic_id": "TA0006", "technique_id": "T1110.003","technique_name": "Brute Force: Password Spraying"},
    ],
    "john": [
        {"tactic_id": "TA0006", "technique_id": "T1110.002","technique_name": "Brute Force: Password Cracking"},
    ],
    "hashcat": [
        {"tactic_id": "TA0006", "technique_id": "T1110.002","technique_name": "Brute Force: Password Cracking"},
    ],

    "metasploit": [
        {"tactic_id": "TA0001", "technique_id": "T1190",    "technique_name": "Exploit Public-Facing Application"},
        {"tactic_id": "TA0002", "technique_id": "T1059",    "technique_name": "Command and Scripting Interpreter"},
        {"tactic_id": "TA0008", "technique_id": "T1210",    "technique_name": "Exploitation of Remote Services"},
    ],
    "msfconsole": [
        {"tactic_id": "TA0001", "technique_id": "T1190",    "technique_name": "Exploit Public-Facing Application"},
        {"tactic_id": "TA0002", "technique_id": "T1059",    "technique_name": "Command and Scripting Interpreter"},
    ],

    "responder": [
        {"tactic_id": "TA0006", "technique_id": "T1557.001","technique_name": "Adversary-in-the-Middle: LLMNR/NBT-NS Poisoning"},
    ],
    "enum4linux": [
        {"tactic_id": "TA0007", "technique_id": "T1087.002","technique_name": "Account Discovery: Domain Account"},
        {"tactic_id": "TA0007", "technique_id": "T1135",    "technique_name": "Network Share Discovery"},
    ],
    "netcat": [
        {"tactic_id": "TA0011", "technique_id": "T1095",    "technique_name": "Non-Application Layer Protocol"},
        {"tactic_id": "TA0007", "technique_id": "T1046",    "technique_name": "Network Service Discovery"},
    ],

    "tshark": [
        {"tactic_id": "TA0009", "technique_id": "T1040",    "technique_name": "Network Sniffing"},
    ],
    "tcpdump": [
        {"tactic_id": "TA0009", "technique_id": "T1040",    "technique_name": "Network Sniffing"},
    ],
    "wireshark": [
        {"tactic_id": "TA0009", "technique_id": "T1040",    "technique_name": "Network Sniffing"},
    ],

    "curl": [
        {"tactic_id": "TA0043", "technique_id": "T1592.002","technique_name": "Gather Victim Host Info: Software"},
        {"tactic_id": "TA0011", "technique_id": "T1071.001","technique_name": "Application Layer Protocol: Web Protocols"},
    ],
    "wget": [
        {"tactic_id": "TA0011", "technique_id": "T1105",    "technique_name": "Ingress Tool Transfer"},
    ],
}


class ATTACKMapper:
    """Maps tools and actions to MITRE ATT&CK techniques.

    Tracks which kill-chain phases have been covered during an investigation
    and suggests the next logical phase.
    """

    def __init__(self) -> None:
        self._mappings: list[TechniqueMapping] = []
        self._kill_chain: dict[str, KillChainPhase] = {}
        self._init_kill_chain()

    def _init_kill_chain(self) -> None:
        """Initialize empty kill chain tracking."""
        for tactic_id, info in TACTICS.items():
            self._kill_chain[tactic_id] = KillChainPhase(
                tactic_id=tactic_id,
                tactic_name=info["name"],
            )

    def map_tool(self, tool_name: str) -> list[TechniqueMapping]:
        """Map a tool to its ATT&CK techniques."""
        tool_lower = tool_name.lower()
        entries = TOOL_TECHNIQUE_MAP.get(tool_lower, [])

        mappings = []
        for entry in entries:
            tactic_id = entry["tactic_id"]
            tactic_info = TACTICS.get(tactic_id, {"name": "Unknown"})

            mapping = TechniqueMapping(
                tool_name=tool_name,
                tactic=tactic_info["name"],
                tactic_id=tactic_id,
                technique_id=entry["technique_id"],
                technique_name=entry["technique_name"],
            )
            mappings.append(mapping)

        return mappings

    def record_execution(
        self,
        tool_name: str,
        status: str = "completed",
    ) -> list[TechniqueMapping]:
        """Record a tool execution and update kill chain coverage."""
        mappings = self.map_tool(tool_name)

        for mapping in mappings:
            self._mappings.append(mapping)
            phase = self._kill_chain.get(mapping.tactic_id)
            if phase:
                tech_id = mapping.technique_id
                if status == "planned" and tech_id not in phase.techniques_planned:
                    phase.techniques_planned.append(tech_id)
                elif status == "executing" and tech_id not in phase.techniques_executed:
                    phase.techniques_executed.append(tech_id)
                elif status == "completed" and tech_id not in phase.techniques_completed:
                    phase.techniques_completed.append(tech_id)
                elif status == "blocked" and tech_id not in phase.techniques_blocked:
                    phase.techniques_blocked.append(tech_id)

                total = len(set(
                    phase.techniques_planned + phase.techniques_executed +
                    phase.techniques_completed + phase.techniques_blocked
                ))
                if total > 0:
                    phase.coverage_pct = (len(phase.techniques_completed) / total) * 100

        return mappings

    def get_kill_chain_status(self) -> list[KillChainPhase]:
        """Return current kill chain coverage status."""
        return list(self._kill_chain.values())

    def get_active_phases(self) -> list[KillChainPhase]:
        """Return phases that have at least one technique."""
        return [
            phase for phase in self._kill_chain.values()
            if (phase.techniques_planned or phase.techniques_executed or
                phase.techniques_completed or phase.techniques_blocked)
        ]

    def suggest_next_phase(self) -> list[dict[str, Any]]:
        """Suggest the next logical ATT&CK phases based on current coverage.

        Follows the typical APT kill chain progression.
        """
        phase_order = [
            "TA0043",
            "TA0042",
            "TA0001",
            "TA0002",
            "TA0003",
            "TA0004",
            "TA0005",
            "TA0006",
            "TA0007",
            "TA0008",
            "TA0009",
            "TA0011",
            "TA0010",
            "TA0040",
        ]

        completed_phases = set()
        for tactic_id, phase in self._kill_chain.items():
            if phase.techniques_completed:
                completed_phases.add(tactic_id)

        suggestions: list[dict[str, Any]] = []
        for tactic_id in phase_order:
            if tactic_id not in completed_phases:
                tactic_info = TACTICS[tactic_id]
                tools = []
                for tool_name, techs in TOOL_TECHNIQUE_MAP.items():
                    if any(t["tactic_id"] == tactic_id for t in techs):
                        tools.append(tool_name)

                suggestions.append({
                    "tactic_id": tactic_id,
                    "tactic_name": tactic_info["name"],
                    "suggested_tools": tools[:5],
                    "priority": "high" if len(suggestions) < 2 else "medium",
                })

                if len(suggestions) >= 3:
                    break

        return suggestions

    def get_all_mappings(self) -> list[TechniqueMapping]:
        """Return all recorded technique mappings."""
        return list(self._mappings)

    def get_coverage_summary(self) -> dict[str, Any]:
        """Return a summary of ATT&CK coverage."""
        total_tactics = len(TACTICS)
        covered_tactics = sum(
            1 for phase in self._kill_chain.values()
            if phase.techniques_completed
        )
        all_techniques = set()
        completed_techniques = set()
        for phase in self._kill_chain.values():
            all_techniques.update(phase.techniques_planned)
            all_techniques.update(phase.techniques_executed)
            all_techniques.update(phase.techniques_completed)
            completed_techniques.update(phase.techniques_completed)

        return {
            "tactics_covered": covered_tactics,
            "tactics_total": total_tactics,
            "tactics_pct": round((covered_tactics / total_tactics) * 100, 1) if total_tactics else 0,
            "techniques_total": len(all_techniques),
            "techniques_completed": len(completed_techniques),
            "techniques_pct": round(
                (len(completed_techniques) / max(1, len(all_techniques))) * 100, 1
            ),
            "total_mappings": len(self._mappings),
        }

    def get_technique_for_id(self, technique_id: str) -> str:
        """Look up a technique name by ID."""
        for tool_techs in TOOL_TECHNIQUE_MAP.values():
            for tech in tool_techs:
                if tech["technique_id"] == technique_id:
                    return tech["technique_name"]
        return "Unknown Technique"

    def reset(self) -> None:
        """Reset all tracking data."""
        self._mappings.clear()
        self._init_kill_chain()
