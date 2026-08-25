"""Signature Evader — manages tool signatures and generates evasion flags.

Maintains a database of known IDS/WAF signatures for each tool and
automatically generates evasion flags to reduce detection risk.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from app.logging_config import get_logger

logger = get_logger("stealth.evasion")


class EvasionSuggestion(BaseModel):
    """A suggested evasion modification for a command."""
    tool: str
    original_args: list[str] = Field(default_factory=list)
    evasion_args: list[str] = Field(default_factory=list)
    evasion_description: str = ""
    signature_avoided: str = ""
    effectiveness: float = 0.0


TOOL_SIGNATURES: dict[str, list[dict[str, str]]] = {
    "nmap": [
        {"signature": "Nmap SYN probe",          "ids": "Snort SID:1228",   "evasion": "Use --data-length to pad packets"},
        {"signature": "Nmap service probe",      "ids": "Suricata ET:2009582", "evasion": "Use -sT instead of -sS for TCP connect"},
        {"signature": "Nmap OS fingerprint",     "ids": "Snort SID:1226",   "evasion": "Avoid -O flag, use banner grabbing instead"},
        {"signature": "Nmap NULL scan",          "ids": "Snort SID:623",    "evasion": "Use -sT TCP connect scan"},
        {"signature": "Nmap XMAS scan",          "ids": "Snort SID:625",    "evasion": "Use -sT TCP connect scan"},
        {"signature": "Nmap scripting engine",   "ids": "Multiple",         "evasion": "Avoid -sC and --script, do manual probing"},
    ],
    "nikto": [
        {"signature": "Nikto User-Agent",        "ids": "Snort SID:2002801","evasion": "Custom User-Agent with -useragent flag"},
        {"signature": "Nikto test patterns",     "ids": "ModSecurity CRS",  "evasion": "Use curl with specific paths instead"},
        {"signature": "Nikto directory traversal","ids": "WAF generic",     "evasion": "Manual path testing with curl"},
    ],
    "sqlmap": [
        {"signature": "SQLMap User-Agent",       "ids": "Snort SID:2019284","evasion": "Use --random-agent flag"},
        {"signature": "SQLMap injection strings", "ids": "ModSecurity CRS", "evasion": "Use --tamper scripts for encoding"},
        {"signature": "SQLMap time-based probes", "ids": "WAF generic",     "evasion": "Use --technique=B for boolean-based only"},
    ],
    "gobuster": [
        {"signature": "Rapid 404 requests",      "ids": "WAF rate limiting","evasion": "Use -t 1 --delay 3s for throttling"},
        {"signature": "Gobuster User-Agent",     "ids": "WAF generic",     "evasion": "Use -a flag with realistic User-Agent"},
    ],
    "masscan": [
        {"signature": "SYN flood pattern",       "ids": "IDS generic",     "evasion": "Use --max-rate 100 to slow down"},
        {"signature": "Masscan banner",          "ids": "Snort SID:2024364","evasion": "Use --banners with randomized source port"},
    ],
    "hydra": [
        {"signature": "Rapid auth attempts",     "ids": "Fail2ban/IDS",    "evasion": "Use -W 5 for wait between attempts"},
        {"signature": "Hydra User-Agent",        "ids": "WAF generic",     "evasion": "Use curl for manual credential testing"},
    ],
    "metasploit": [
        {"signature": "Meterpreter beacon",      "ids": "Multiple EDR",    "evasion": "Use custom stagers or LOLBins"},
        {"signature": "MSF exploit payloads",    "ids": "AV/EDR generic",  "evasion": "Use manual exploitation techniques"},
    ],
    "responder": [
        {"signature": "LLMNR/NBT-NS poisoning",  "ids": "Sysmon Event 22","evasion": "Use targeted approaches instead of broadcast"},
    ],
    "nuclei": [
        {"signature": "Nuclei User-Agent",       "ids": "WAF generic",     "evasion": "Use -H 'User-Agent: Mozilla/5.0...'"},
        {"signature": "Nuclei template patterns", "ids": "WAF generic",     "evasion": "Use -rl 5 for rate limiting"},
    ],
}

EVASION_FLAGS: dict[str, list[dict[str, Any]]] = {
    "nmap": [
        {
            "flags": ["--randomize-hosts"],
            "description": "Randomize target host order to avoid sequential scanning patterns",
            "effectiveness": 0.3,
        },
        {
            "flags": ["--data-length", "24"],
            "description": "Pad packets with random data to evade length-based signatures",
            "effectiveness": 0.4,
        },
        {
            "flags": ["-f"],
            "description": "Fragment packets to bypass simple packet inspection",
            "effectiveness": 0.5,
        },
        {
            "flags": ["-D", "RND:5"],
            "description": "Use 5 random decoy IP addresses to obscure scan source",
            "effectiveness": 0.6,
        },
        {
            "flags": ["--source-port", "53"],
            "description": "Use DNS source port (53) — often allowed through firewalls",
            "effectiveness": 0.4,
        },
        {
            "flags": ["-T2"],
            "description": "Polite timing template — significantly reduces traffic rate",
            "effectiveness": 0.5,
        },
        {
            "flags": ["--max-rate", "10"],
            "description": "Limit to 10 packets/second — well below IDS thresholds",
            "effectiveness": 0.6,
        },
        {
            "flags": ["-sT"],
            "description": "TCP connect scan — completes handshake, less anomalous than SYN",
            "effectiveness": 0.3,
        },
    ],
    "nikto": [
        {
            "flags": ["-useragent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"],
            "description": "Realistic Chrome User-Agent to bypass UA-based detection",
            "effectiveness": 0.5,
        },
        {
            "flags": ["-Pause", "3"],
            "description": "3-second pause between requests to avoid rate limiting",
            "effectiveness": 0.4,
        },
    ],
    "sqlmap": [
        {
            "flags": ["--random-agent"],
            "description": "Use a random User-Agent for each request",
            "effectiveness": 0.4,
        },
        {
            "flags": ["--tamper", "between,randomcase,space2comment"],
            "description": "Apply tamper scripts to encode payloads and evade WAF rules",
            "effectiveness": 0.7,
        },
        {
            "flags": ["--delay", "3"],
            "description": "3-second delay between requests to avoid rate-based detection",
            "effectiveness": 0.4,
        },
        {
            "flags": ["--safe-url", "/", "--safe-freq", "5"],
            "description": "Visit safe URL every 5 requests to maintain session and look legitimate",
            "effectiveness": 0.3,
        },
    ],
    "gobuster": [
        {
            "flags": ["-t", "1", "--delay", "3s"],
            "description": "Single thread with 3s delay — mimics manual browsing",
            "effectiveness": 0.6,
        },
        {
            "flags": ["-a", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"],
            "description": "Realistic browser User-Agent",
            "effectiveness": 0.3,
        },
    ],
    "masscan": [
        {
            "flags": ["--max-rate", "100"],
            "description": "Limit to 100 packets/second — dramatically reduces visibility",
            "effectiveness": 0.5,
        },
        {
            "flags": ["--randomize-hosts"],
            "description": "Randomize target order within ranges",
            "effectiveness": 0.3,
        },
    ],
    "nuclei": [
        {
            "flags": ["-rl", "5"],
            "description": "Rate limit to 5 requests/second",
            "effectiveness": 0.5,
        },
        {
            "flags": ["-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)"],
            "description": "Realistic browser User-Agent header",
            "effectiveness": 0.3,
        },
    ],
    "hydra": [
        {
            "flags": ["-W", "5"],
            "description": "5-second wait between connection attempts",
            "effectiveness": 0.4,
        },
        {
            "flags": ["-t", "1"],
            "description": "Single thread — looks like normal login attempts",
            "effectiveness": 0.5,
        },
    ],
}


class SignatureEvader:
    """Manages tool signatures and generates evasion modifications.

    Given a tool command, applies evasion techniques to reduce the likelihood
    of triggering IDS/WAF/EDR signatures.
    """

    def __init__(self) -> None:
        self._evasion_history: list[dict[str, Any]] = []

    def get_known_signatures(self, tool_name: str) -> list[dict[str, str]]:
        """Return known IDS/WAF signatures for a tool."""
        return TOOL_SIGNATURES.get(tool_name.lower(), [])

    def get_evasion_flags(self, tool_name: str) -> list[dict[str, Any]]:
        """Return available evasion flag sets for a tool."""
        return EVASION_FLAGS.get(tool_name.lower(), [])

    def generate_evasion(
        self,
        tool_name: str,
        original_args: list[str],
        stealth_level: str = "careful",
    ) -> EvasionSuggestion:
        """Generate evasion modifications for a command.

        Args:
            tool_name: The tool being used.
            original_args: The original arguments.
            stealth_level: How aggressively to evade.
                'paranoid' — apply all possible evasion flags.
                'careful' — apply flags with effectiveness > 0.4.
                'normal' — apply only the most effective flag.
                'aggressive' — no evasion (speed priority).
        """
        tool_lower = tool_name.lower()
        available_flags = EVASION_FLAGS.get(tool_lower, [])

        if not available_flags or stealth_level == "aggressive":
            return EvasionSuggestion(
                tool=tool_name,
                original_args=original_args,
                evasion_args=list(original_args),
                evasion_description="No evasion applied",
                effectiveness=0.0,
            )

        effectiveness_threshold = {
            "paranoid": 0.0,
            "careful":  0.4,
            "normal":   0.6,
        }.get(stealth_level, 0.4)

        selected_flags: list[str] = []
        descriptions: list[str] = []
        signatures_avoided: list[str] = []
        total_effectiveness = 0.0
        count = 0

        for flag_set in available_flags:
            if flag_set["effectiveness"] >= effectiveness_threshold:
                flag_str = " ".join(flag_set["flags"])
                args_str = " ".join(original_args)
                if flag_set["flags"][0] not in args_str:
                    selected_flags.extend(flag_set["flags"])
                    descriptions.append(flag_set["description"])
                    total_effectiveness += flag_set["effectiveness"]
                    count += 1

        evaded_args = list(original_args)

        if tool_lower == "nmap":
            if any("-T2" in f for f in selected_flags):
                evaded_args = [a for a in evaded_args if not re.match(r"-T[3-5]", a)]

        evaded_args.extend(selected_flags)

        tool_sigs = TOOL_SIGNATURES.get(tool_lower, [])
        for sig in tool_sigs:
            signatures_avoided.append(sig["signature"])

        avg_effectiveness = (total_effectiveness / max(1, count))

        suggestion = EvasionSuggestion(
            tool=tool_name,
            original_args=original_args,
            evasion_args=evaded_args,
            evasion_description="; ".join(descriptions) if descriptions else "No modifications applied",
            signature_avoided=", ".join(signatures_avoided[:3]) if signatures_avoided else "",
            effectiveness=round(min(1.0, avg_effectiveness), 2),
        )

        self._evasion_history.append({
            "tool": tool_name,
            "flags_added": len(selected_flags),
            "effectiveness": suggestion.effectiveness,
        })

        logger.info(
            "Evasion for %s: added %d flags, effectiveness %.0f%%",
            tool_name, len(selected_flags), suggestion.effectiveness * 100,
        )
        return suggestion

    def apply_evasion_to_args(
        self,
        tool_name: str,
        original_args: list[str],
        stealth_level: str = "careful",
    ) -> list[str]:
        """Convenience: return just the evaded argument list."""
        suggestion = self.generate_evasion(tool_name, original_args, stealth_level)
        return suggestion.evasion_args

    def get_statistics(self) -> dict[str, Any]:
        """Return evasion statistics."""
        if not self._evasion_history:
            return {"total_evasions": 0, "avg_effectiveness": 0.0}

        return {
            "total_evasions": len(self._evasion_history),
            "avg_effectiveness": round(
                sum(e["effectiveness"] for e in self._evasion_history) / len(self._evasion_history),
                2,
            ),
            "total_flags_added": sum(e["flags_added"] for e in self._evasion_history),
        }
