from __future__ import annotations

import asyncio
from typing import Any

from app.execution.models import CommandPlan
from app.execution.manager import ExecutionManager
from app.osint.connectors.base import BaseOSINTConnector
from app.osint.models import OSINTResult, EntityType
from app.logging_config import get_logger

logger = get_logger("osint.connectors.dns")


class DNSConnector(BaseOSINTConnector):
    CONNECTOR_NAME = "dns"
    SUPPORTED_ENTITIES = [EntityType.DOMAIN, EntityType.IP, EntityType.SUBDOMAIN]

    def __init__(self, execution_manager: ExecutionManager | None = None) -> None:
        self._exec_manager = execution_manager

    async def search(self, entity_type: EntityType, value: str, **kwargs: Any) -> list[OSINTResult]:
        results: list[OSINTResult] = []

        if entity_type in (EntityType.DOMAIN, EntityType.SUBDOMAIN):
            for record_type in ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]:
                try:
                    records = await self._resolve(value, record_type)
                    for record in records:
                        results.append(OSINTResult(
                            source="dns",
                            entity_type="dns_record",
                            value=record,
                            confidence=1.0,
                            evidence=f"{record_type} record for {value}",
                            relationships=[{
                                "type": "has_dns_record",
                                "from": value,
                                "to": record,
                                "record_type": record_type,
                            }],
                        ))
                except Exception as e:
                    logger.debug("DNS lookup failed for %s %s: %s", value, record_type, e)

        elif entity_type == EntityType.IP:
            try:
                ptr = await self._resolve_ptr(value)
                if ptr:
                    results.append(OSINTResult(
                        source="dns",
                        entity_type="hostname",
                        value=ptr,
                        confidence=0.9,
                        evidence=f"PTR record for {value}",
                        relationships=[{"type": "resolves_to", "from": ptr, "to": value}],
                    ))
            except Exception as e:
                logger.debug("PTR lookup failed for %s: %s", value, e)

        return results

    async def _resolve(self, domain: str, record_type: str) -> list[str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "nslookup", "-type=" + record_type, domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            output = stdout.decode("utf-8", errors="replace")
            records = []
            for line in output.split("\n"):
                line = line.strip()
                if "=" in line and "address" in line.lower():
                    records.append(line.split("=")[-1].strip())
                elif line and not line.startswith("#") and "." in line and "server" not in line.lower():
                    parts = line.split()
                    if parts:
                        records.append(parts[-1].strip().rstrip("."))
            return records
        except Exception:
            return []

    async def _resolve_ptr(self, ip: str) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "nslookup", ip,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            output = stdout.decode("utf-8", errors="replace")
            for line in output.split("\n"):
                if "name" in line.lower() and "=" in line:
                    return line.split("=")[-1].strip().rstrip(".")
            return ""
        except Exception:
            return ""

    async def health_check(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "nslookup", "google.com",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            return proc.returncode == 0
        except Exception:
            return False
