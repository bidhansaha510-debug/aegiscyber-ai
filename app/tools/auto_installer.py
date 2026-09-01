from __future__ import annotations

import re
from datetime import datetime, timezone

from app.config import get_config
from app.execution.manager import ExecutionManager
from app.execution.models import CommandPlan, ExecutionRequest, ExecutionResult, ExecutionStatus
from app.tools.registry import ToolRegistry
from app.tools.schemas import InstalledTool
from app.logging_config import get_logger

logger = get_logger("tools.auto_installer")

# Patterns that indicate the executed binary does not exist in the backend.
# Capture groups (when present) extract the missing binary name.
MISSING_TOOL_PATTERNS: list[str] = [
    r"(?:bash|sh|zsh):\s*(\S+):\s*command not found",
    r"command not found:\s*(\S+)",
    r"(\S+):\s*command not found",
    r"(\S+):\s*No such file or directory",
    r"no such file or directory:\s*(\S+)",
    r"'(\S+)'\s+is not recognized as an internal or external command",
    r"program\s+'(\S+)'\s+is currently not installed",
    r"(\S+):\s*not found\b",
]

# Common binary -> apt package mapping for Kali/Debian backends.
PACKAGE_MAP: dict[str, str] = {
    "nmap": "nmap",
    "ncat": "nmap",
    "nikto": "nikto",
    "sqlmap": "sqlmap",
    "hydra": "hydra",
    "gobuster": "gobuster",
    "ffuf": "ffuf",
    "wfuzz": "wfuzz",
    "dirb": "dirb",
    "dirsearch": "dirsearch",
    "whatweb": "whatweb",
    "sslscan": "sslscan",
    "testssl": "testssl.sh",
    "testssl.sh": "testssl.sh",
    "nuclei": "nuclei",
    "subfinder": "subfinder",
    "amass": "amass",
    "httpx": "httpx-toolkit",
    "dnsx": "dnsx",
    "dnsrecon": "dnsrecon",
    "dig": "dnsutils",
    "host": "bind9-dnsutils",
    "nslookup": "dnsutils",
    "whois": "whois",
    "masscan": "masscan",
    "enum4linux": "enum4linux",
    "enum4linux-ng": "enum4linux-ng",
    "smbclient": "smbclient",
    "smbmap": "smbmap",
    "netexec": "netexec",
    "crackmapexec": "netexec",
    "responder": "responder",
    "wpscan": "wpscan",
    "joomscan": "joomscan",
    "droopescan": "droopescan",
    "commix": "commix",
    "dalfox": "dalfox",
    "xsstrike": "xsstrike",
    "arjun": "arjun",
    "john": "john",
    "hashcat": "hashcat",
    "theharvester": "theharvester",
    "sherlock": "sherlock",
    "traceroute": "traceroute",
    "nc": "netcat-openbsd",
    "netcat": "netcat-openbsd",
    "curl": "curl",
    "openssl": "openssl",
    "ping": "iputils-ping",
    "python3": "python3",
    "feroxbuster": "feroxbuster",
    "nbtscan": "nbtscan",
    "onesixtyone": "onesixtyone",
    "snmpwalk": "snmp",
    "ldapsearch": "ldap-utils",
    "wafw00f": "wafw00f",
}


class ToolAutoInstaller:
    """Detects 'tool missing' failures and installs the tool into the backend."""

    def __init__(self, exec_manager: ExecutionManager, tool_registry: ToolRegistry) -> None:
        self._exec_manager = exec_manager
        self._registry = tool_registry
        self._config = get_config()
        self._install_lock_attempts: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    def is_missing_tool_error(self, exec_result: ExecutionResult, backend: str = "") -> bool:
        """True when the failure looks like 'binary not found' (e.g. exit 127)."""
        if exec_result.exit_code == 127:
            return True
        combined = self._error_text(exec_result).lower()
        if not combined:
            return False
        for pattern in MISSING_TOOL_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return True
        return False

    def extract_missing_binary(self, exec_result: ExecutionResult, fallback: str = "") -> str:
        """Extract the name of the missing binary from the error output."""
        combined = self._error_text(exec_result)
        for pattern in MISSING_TOOL_PATTERNS:
            m = re.search(pattern, combined, re.IGNORECASE)
            if m and m.groups():
                candidate = m.group(1).strip("'\"")
                candidate = candidate.rsplit("/", 1)[-1]
                # Reject obvious non-binary matches (paths with extensions etc.)
                if candidate and "." not in candidate and len(candidate) < 40:
                    return candidate
        return (fallback or exec_result.tool_name or "").strip()

    def get_package_for(self, binary: str) -> str:
        binary = binary.strip().lower()
        pkg = PACKAGE_MAP.get(binary, "")
        if pkg:
            return pkg
        return binary

    # ------------------------------------------------------------------
    # Installation
    # ------------------------------------------------------------------
    async def install_tool(
        self,
        binary: str,
        backend: str = "wsl2",
        investigation_id: str = "",
    ) -> tuple[bool, str]:
        """Install `binary` into the given backend. Returns (success, message)."""
        if not binary:
            return False, "No missing binary identified"

        pkg = self.get_package_for(binary)
        if not pkg:
            return False, f"No known package for '{binary}'"

        if not self._exec_manager.is_backend_available(backend):
            return False, f"Backend '{backend}' unavailable - cannot auto-install"

        attempts = self._install_lock_attempts.get(f"{binary}:{backend}", 0)
        if attempts >= 2:
            return False, f"Install for '{binary}' already attempted twice - skipping"

        self._install_lock_attempts[f"{binary}:{backend}"] = attempts + 1

        apt_cmd = (
            "apt-get update -qq; "
            f"DEBIAN_FRONTEND=noninteractive apt-get install -y {pkg} "
            f"|| sudo -n DEBIAN_FRONTEND=noninteractive apt-get install -y {pkg}"
        )
        install_plan = CommandPlan(
            executable="bash",
            arguments=["-c", apt_cmd],
            target="",
            timeout=self._config.selfheal.install_timeout,
            backend=backend,
            explanation=f"Auto-install missing tool '{binary}' (package: {pkg})",
        )

        logger.info("Auto-installing missing tool '%s' via package '%s' on %s", binary, pkg, backend)

        result = await self._exec_manager.execute(ExecutionRequest(
            task_id=investigation_id,
            command_plan=install_plan,
        ))

        success = result.status == ExecutionStatus.COMPLETED

        # Verify the binary is actually present now and refresh registry state.
        verified = ""
        if success:
            try:
                exists, path, version = await self._exec_manager.check_tool(binary, backend)
                if exists:
                    verified = f" (verified: {path} {version})".rstrip()
                    self._registry.set_installed(binary, backend, InstalledTool(
                        name=binary,
                        backend=backend,
                        version=version,
                        path=path,
                        is_available=True,
                        last_checked=datetime.now(timezone.utc).isoformat(),
                    ))
                else:
                    logger.warning("Install of '%s' claimed success but binary not found afterwards", binary)
            except Exception as e:
                logger.warning("Post-install verification of '%s' failed: %s", binary, e)

        if success:
            msg = f"Installed '{binary}' (package: {pkg}){verified}"
        else:
            tail = (result.stderr or result.stdout or result.error_message or "").strip()[-200:]
            msg = f"Failed to install '{binary}' (package: {pkg}): {tail}"

        return success, msg

    # ------------------------------------------------------------------
    def _error_text(self, exec_result: ExecutionResult) -> str:
        parts = [exec_result.error_message, exec_result.stderr, exec_result.stdout]
        return "\n".join(p for p in parts if p)
