"""OPSEC Engine — assigns risk scores and suggests stealth alternatives.

Every command is evaluated for detection risk before execution.  The engine
considers signature detectability, traffic volume, log footprint, and
timing profile to produce a 0-100 OPSEC score (lower = stealthier).
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from app.logging_config import get_logger

logger = get_logger("stealth.opsec")


TOOL_NOISE_PROFILES: dict[str, dict[str, Any]] = {
    "nmap":       {"detection_weight": 85, "traffic_volume": "high",   "signature_count": 42, "log_footprint": "high"},
    "masscan":    {"detection_weight": 90, "traffic_volume": "extreme","signature_count": 12, "log_footprint": "high"},
    "nikto":      {"detection_weight": 92, "traffic_volume": "high",   "signature_count": 38, "log_footprint": "high"},
    "gobuster":   {"detection_weight": 80, "traffic_volume": "high",   "signature_count": 8,  "log_footprint": "medium"},
    "ffuf":       {"detection_weight": 78, "traffic_volume": "high",   "signature_count": 5,  "log_footprint": "medium"},
    "sqlmap":     {"detection_weight": 95, "traffic_volume": "high",   "signature_count": 60, "log_footprint": "high"},
    "nuclei":     {"detection_weight": 75, "traffic_volume": "medium", "signature_count": 20, "log_footprint": "medium"},
    "hydra":      {"detection_weight": 88, "traffic_volume": "high",   "signature_count": 15, "log_footprint": "high"},

    "subfinder":  {"detection_weight": 30, "traffic_volume": "low",    "signature_count": 2,  "log_footprint": "low"},
    "amass":      {"detection_weight": 45, "traffic_volume": "medium", "signature_count": 5,  "log_footprint": "medium"},
    "httpx":      {"detection_weight": 40, "traffic_volume": "medium", "signature_count": 3,  "log_footprint": "low"},
    "dnsx":       {"detection_weight": 35, "traffic_volume": "medium", "signature_count": 2,  "log_footprint": "low"},
    "enum4linux": {"detection_weight": 70, "traffic_volume": "medium", "signature_count": 10, "log_footprint": "medium"},
    "netcat":     {"detection_weight": 50, "traffic_volume": "low",    "signature_count": 3,  "log_footprint": "low"},

    "dig":        {"detection_weight": 10, "traffic_volume": "minimal","signature_count": 0,  "log_footprint": "minimal"},
    "whois":      {"detection_weight": 8,  "traffic_volume": "minimal","signature_count": 0,  "log_footprint": "minimal"},
    "curl":       {"detection_weight": 12, "traffic_volume": "low",    "signature_count": 0,  "log_footprint": "low"},
    "wget":       {"detection_weight": 15, "traffic_volume": "low",    "signature_count": 1,  "log_footprint": "low"},
    "openssl":    {"detection_weight": 10, "traffic_volume": "minimal","signature_count": 0,  "log_footprint": "minimal"},
    "tshark":     {"detection_weight": 5,  "traffic_volume": "none",   "signature_count": 0,  "log_footprint": "minimal"},
    "tcpdump":    {"detection_weight": 5,  "traffic_volume": "none",   "signature_count": 0,  "log_footprint": "minimal"},

    "metasploit": {"detection_weight": 98, "traffic_volume": "high",   "signature_count": 200,"log_footprint": "extreme"},
    "msfconsole": {"detection_weight": 98, "traffic_volume": "high",   "signature_count": 200,"log_footprint": "extreme"},
    "responder":  {"detection_weight": 95, "traffic_volume": "medium", "signature_count": 25, "log_footprint": "high"},
    "john":       {"detection_weight": 20, "traffic_volume": "none",   "signature_count": 0,  "log_footprint": "low"},
    "hashcat":    {"detection_weight": 15, "traffic_volume": "none",   "signature_count": 0,  "log_footprint": "low"},
}

EDR_DETECTION_MATRICES: dict[str, dict[str, float]] = {
    "crowdstrike": {
        "network_scanning": 0.95, "web_scanning": 0.90, "brute_force": 0.92,
        "credential_dumping": 0.98, "lateral_movement": 0.93, "lolbin_abuse": 0.60,
        "dns_enumeration": 0.30, "passive_recon": 0.10, "encrypted_c2": 0.45,
    },
    "sentinelone": {
        "network_scanning": 0.90, "web_scanning": 0.85, "brute_force": 0.88,
        "credential_dumping": 0.95, "lateral_movement": 0.90, "lolbin_abuse": 0.55,
        "dns_enumeration": 0.25, "passive_recon": 0.08, "encrypted_c2": 0.40,
    },
    "elastic_siem": {
        "network_scanning": 0.85, "web_scanning": 0.80, "brute_force": 0.85,
        "credential_dumping": 0.80, "lateral_movement": 0.78, "lolbin_abuse": 0.45,
        "dns_enumeration": 0.40, "passive_recon": 0.15, "encrypted_c2": 0.35,
    },
    "splunk_es": {
        "network_scanning": 0.80, "web_scanning": 0.75, "brute_force": 0.82,
        "credential_dumping": 0.75, "lateral_movement": 0.72, "lolbin_abuse": 0.40,
        "dns_enumeration": 0.35, "passive_recon": 0.12, "encrypted_c2": 0.30,
    },
    "microsoft_defender": {
        "network_scanning": 0.70, "web_scanning": 0.65, "brute_force": 0.75,
        "credential_dumping": 0.90, "lateral_movement": 0.80, "lolbin_abuse": 0.65,
        "dns_enumeration": 0.20, "passive_recon": 0.05, "encrypted_c2": 0.50,
    },
}

TOOL_ATTACK_TYPE: dict[str, str] = {
    "nmap": "network_scanning", "masscan": "network_scanning",
    "nikto": "web_scanning", "gobuster": "web_scanning", "ffuf": "web_scanning",
    "sqlmap": "web_scanning", "nuclei": "web_scanning",
    "hydra": "brute_force", "john": "credential_dumping", "hashcat": "credential_dumping",
    "responder": "lateral_movement", "enum4linux": "lateral_movement",
    "metasploit": "lateral_movement", "msfconsole": "lateral_movement",
    "dig": "dns_enumeration", "dnsx": "dns_enumeration", "whois": "passive_recon",
    "subfinder": "passive_recon", "amass": "dns_enumeration",
    "curl": "passive_recon", "wget": "passive_recon",
    "tshark": "passive_recon", "tcpdump": "passive_recon",
    "openssl": "passive_recon", "httpx": "web_scanning",
    "netcat": "lateral_movement",
}

NOISY_ARGUMENT_PATTERNS: list[tuple[re.Pattern, int, str]] = [
    (re.compile(r"-sV", re.IGNORECASE),           15, "Service version probing generates unique signatures"),
    (re.compile(r"-sC|--script", re.IGNORECASE),   20, "NSE scripts are heavily signatured"),
    (re.compile(r"-A|--aggressive", re.IGNORECASE), 25, "Aggressive scan mode is trivially detected"),
    (re.compile(r"-T[45]", re.IGNORECASE),          10, "Fast timing increases traffic anomaly detection"),
    (re.compile(r"-p-|1-65535", re.IGNORECASE),     20, "Full port scans create massive traffic spikes"),
    (re.compile(r"--script=vuln", re.IGNORECASE),   30, "Vulnerability scripts trigger IDS alerts"),
    (re.compile(r"-oG|-oX|-oN", re.IGNORECASE),     0,  "Output format flags are benign"),
    (re.compile(r"--crawl|--forms", re.IGNORECASE),  15, "Automated crawling triggers WAF rules"),
    (re.compile(r"--batch", re.IGNORECASE),          5,  "Batch mode may speed up detection"),
    (re.compile(r"--level=[3-5]", re.IGNORECASE),    20, "High SQLMap levels increase request volume dramatically"),
    (re.compile(r"--risk=[2-3]", re.IGNORECASE),     25, "High SQLMap risk includes destructive tests"),
]


class StealthAlternative(BaseModel):
    """A stealthier alternative to a noisy command."""
    original_tool: str
    alternative_tool: str
    alternative_command: str
    opsec_improvement: int
    trade_off: str
    technique_description: str


class EDRDetection(BaseModel):
    """Detection likelihood against a specific EDR/SOC stack."""
    edr_name: str
    detection_probability: float
    attack_type: str
    notes: str = ""


class OPSECScore(BaseModel):
    """OPSEC risk assessment for a command. Lower = stealthier."""
    total_score: int = 0
    base_tool_risk: int = 0
    argument_penalty: int = 0
    traffic_penalty: int = 0
    timing_bonus: int = 0
    risk_label: str = "UNKNOWN"
    detection_notes: list[str] = Field(default_factory=list)
    edr_detections: list[EDRDetection] = Field(default_factory=list)
    stealth_alternatives: list[StealthAlternative] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


STEALTH_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "nmap": [
        {
            "tool": "curl",
            "command": "curl -s -o /dev/null -w '%{{http_code}}' http://{target}:{port}",
            "trade_off": "Only checks HTTP ports, no service fingerprinting",
            "description": "HTTP probe via curl — indistinguishable from normal web traffic",
        },
        {
            "tool": "bash",
            "command": "echo '' > /dev/tcp/{target}/{port} 2>/dev/null && echo 'open' || echo 'closed'",
            "trade_off": "No service detection, single port per invocation",
            "description": "Bash /dev/tcp port check — no tool installation needed, no signature",
        },
        {
            "tool": "openssl",
            "command": "openssl s_client -connect {target}:{port} -servername {target} </dev/null 2>/dev/null",
            "trade_off": "Only works on TLS-enabled services",
            "description": "OpenSSL TLS probe — looks like normal HTTPS negotiation",
        },
    ],
    "nikto": [
        {
            "tool": "curl",
            "command": "curl -s -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' -D - http://{target}/",
            "trade_off": "No vulnerability scanning, just header/banner grabbing",
            "description": "Curl with realistic User-Agent — mimics browser request",
        },
    ],
    "gobuster": [
        {
            "tool": "curl",
            "command": "for path in admin login api docs; do curl -s -o /dev/null -w '%{{http_code}} {target}/$path\\n' http://{target}/$path; sleep $((RANDOM % 5 + 2)); done",
            "trade_off": "Much slower, limited wordlist",
            "description": "Manual path probing with randomized delays — avoids brute-force signatures",
        },
    ],
    "sqlmap": [
        {
            "tool": "curl",
            "command": "curl -s 'http://{target}/page?id=1%27' | grep -i 'error\\|sql\\|syntax\\|mysql\\|postgresql'",
            "trade_off": "Single probe only, no automated exploitation",
            "description": "Manual SQL injection test via curl — single request, no automation signature",
        },
    ],
    "masscan": [
        {
            "tool": "nmap",
            "command": "nmap -T2 --randomize-hosts --data-length 24 -sS --max-rate 10 -p {ports} {target}",
            "trade_off": "Much slower scan speed",
            "description": "Slow nmap with randomization — reduces traffic anomaly detection",
        },
    ],
    "hydra": [
        {
            "tool": "curl",
            "command": "curl -s -X POST -d 'username={user}&password={pass}' http://{target}/login -w '%{{http_code}}'",
            "trade_off": "No parallelism, manual credential iteration",
            "description": "Manual credential test via curl — looks like normal login attempt",
        },
    ],
}


class OPSECEngine:
    """Central stealth orchestrator for APT-grade OPSEC awareness.

    Evaluates every command for detection risk before execution and suggests
    stealth alternatives when a noisy tool is selected.
    """

    def __init__(self) -> None:
        self._stealth_mode: bool = False
        self._active_edr_profiles: list[str] = list(EDR_DETECTION_MATRICES.keys())
        self._custom_tool_profiles: dict[str, dict[str, Any]] = {}
        self._execution_history: list[dict[str, Any]] = []

    @property
    def stealth_mode(self) -> bool:
        return self._stealth_mode

    @stealth_mode.setter
    def stealth_mode(self, value: bool) -> None:
        self._stealth_mode = value
        logger.info("Stealth mode %s", "ENGAGED" if value else "disengaged")

    def set_target_edr(self, edr_names: list[str]) -> None:
        """Configure which EDR/SOC stacks the target is known to run."""
        valid = [n for n in edr_names if n in EDR_DETECTION_MATRICES]
        self._active_edr_profiles = valid or list(EDR_DETECTION_MATRICES.keys())
        logger.info("Target EDR profiles set: %s", self._active_edr_profiles)

    def evaluate_command(
        self,
        executable: str,
        arguments: list[str],
        target: str = "",
    ) -> OPSECScore:
        """Evaluate a command's OPSEC risk. Returns a score 0-100."""
        score = OPSECScore()
        exec_base = executable.lower().split("/")[-1].split("\\")[-1]
        args_string = " ".join(arguments)

        profile = TOOL_NOISE_PROFILES.get(exec_base, self._custom_tool_profiles.get(exec_base))
        if profile:
            score.base_tool_risk = profile["detection_weight"]
            if profile["traffic_volume"] in ("high", "extreme"):
                score.detection_notes.append(
                    f"{exec_base} generates {profile['traffic_volume']} traffic volume"
                )
            if profile["signature_count"] > 10:
                score.detection_notes.append(
                    f"{exec_base} has {profile['signature_count']} known IDS/EDR signatures"
                )
        else:
            score.base_tool_risk = 40
            score.detection_notes.append(
                f"No noise profile for '{exec_base}' — using moderate default"
            )

        for pattern, penalty, note in NOISY_ARGUMENT_PATTERNS:
            if pattern.search(args_string):
                score.argument_penalty += penalty
                score.detection_notes.append(note)

        if profile:
            volume_penalties = {
                "extreme": 15, "high": 10, "medium": 5,
                "low": 0, "minimal": -5, "none": -10,
            }
            score.traffic_penalty = volume_penalties.get(profile["traffic_volume"], 0)

        raw = score.base_tool_risk + score.argument_penalty + score.traffic_penalty + score.timing_bonus
        score.total_score = max(0, min(100, raw))

        if score.total_score <= 15:
            score.risk_label = "GHOST"
        elif score.total_score <= 30:
            score.risk_label = "LOW"
        elif score.total_score <= 50:
            score.risk_label = "MODERATE"
        elif score.total_score <= 70:
            score.risk_label = "HIGH"
        elif score.total_score <= 85:
            score.risk_label = "LOUD"
        else:
            score.risk_label = "COMPROMISED"

        attack_type = TOOL_ATTACK_TYPE.get(exec_base, "passive_recon")
        for edr_name in self._active_edr_profiles:
            matrix = EDR_DETECTION_MATRICES.get(edr_name, {})
            detection_prob = matrix.get(attack_type, 0.5)
            adjusted = min(1.0, detection_prob + (score.argument_penalty / 200))
            score.edr_detections.append(EDRDetection(
                edr_name=edr_name,
                detection_probability=round(adjusted, 2),
                attack_type=attack_type,
            ))

        alternatives = STEALTH_ALTERNATIVES.get(exec_base, [])
        for alt in alternatives:
            alt_profile = TOOL_NOISE_PROFILES.get(alt["tool"], {})
            alt_risk = alt_profile.get("detection_weight", 30)
            improvement = score.base_tool_risk - alt_risk
            if improvement > 0:
                score.stealth_alternatives.append(StealthAlternative(
                    original_tool=exec_base,
                    alternative_tool=alt["tool"],
                    alternative_command=alt["command"].format(
                        target=target or "{target}",
                        port="443",
                        ports="80,443",
                        user="{user}",
                        pass_="{pass}",
                    ),
                    opsec_improvement=improvement,
                    trade_off=alt["trade_off"],
                    technique_description=alt["description"],
                ))

        if score.total_score > 60:
            score.recommendations.append("Consider using a LOLBin alternative for this task")
            score.recommendations.append("Add jitter (randomized delays) between requests")
        if score.total_score > 40:
            score.recommendations.append("Use --randomize-hosts if available")
            score.recommendations.append("Limit scan rate to blend with normal traffic")
        if any(p.search(args_string) for p, _, _ in NOISY_ARGUMENT_PATTERNS[:3]):
            score.recommendations.append("Remove aggressive scan flags to reduce signature matches")

        self._execution_history.append({
            "executable": exec_base,
            "score": score.total_score,
            "label": score.risk_label,
        })

        logger.info(
            "OPSEC score for %s: %d (%s) — %d EDR detections, %d alternatives",
            exec_base, score.total_score, score.risk_label,
            len(score.edr_detections), len(score.stealth_alternatives),
        )
        return score

    def get_opsec_summary(self) -> dict[str, Any]:
        """Return a summary of OPSEC scores from this session."""
        if not self._execution_history:
            return {"avg_score": 0, "total_commands": 0, "risk_distribution": {}}

        scores = [e["score"] for e in self._execution_history]
        labels = [e["label"] for e in self._execution_history]
        distribution: dict[str, int] = {}
        for lbl in labels:
            distribution[lbl] = distribution.get(lbl, 0) + 1

        return {
            "avg_score": round(sum(scores) / len(scores), 1),
            "total_commands": len(self._execution_history),
            "risk_distribution": distribution,
            "stealth_mode": self._stealth_mode,
        }

    def should_block_in_stealth(self, score: OPSECScore, threshold: int = 70) -> bool:
        """In stealth mode, block commands above the OPSEC threshold."""
        if not self._stealth_mode:
            return False
        return score.total_score >= threshold
