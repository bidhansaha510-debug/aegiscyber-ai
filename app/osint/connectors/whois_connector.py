from __future__ import annotations

import asyncio
from typing import Any

from app.osint.connectors.base import BaseOSINTConnector
from app.osint.models import OSINTResult, EntityType
from app.logging_config import get_logger

logger = get_logger("osint.connectors.whois")


class WhoisConnector(BaseOSINTConnector):
    CONNECTOR_NAME = "whois"
    SUPPORTED_ENTITIES = [EntityType.DOMAIN, EntityType.IP]

    async def search(self, entity_type: EntityType, value: str, **kwargs: Any) -> list[OSINTResult]:
        results: list[OSINTResult] = []

        try:
            proc = await asyncio.create_subprocess_exec(
                "whois", value,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            output = stdout.decode("utf-8", errors="replace")

            if output.strip():
                parsed = self._parse_whois(output)
                results.append(OSINTResult(
                    source="whois",
                    entity_type=entity_type.value,
                    value=value,
                    confidence=0.95,
                    evidence=f"WHOIS lookup for {value}",
                    raw_data=parsed,
                    relationships=self._extract_relationships(value, parsed),
                ))
        except Exception as e:
            logger.error("WHOIS lookup failed for %s: %s", value, e)

        return results

    def _parse_whois(self, output: str) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for line in output.split("\n"):
            line = line.strip()
            if not line or line.startswith("%") or line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip()
                if key and value:
                    if key in data:
                        if isinstance(data[key], list):
                            data[key].append(value)
                        else:
                            data[key] = [data[key], value]
                    else:
                        data[key] = value
        return data

    def _extract_relationships(self, target: str, parsed: dict[str, Any]) -> list[dict[str, Any]]:
        relationships = []

        registrar = parsed.get("registrar", "")
        if registrar:
            relationships.append({
                "type": "registered_by",
                "from": target,
                "to": registrar if isinstance(registrar, str) else registrar[0],
            })

        ns_keys = [k for k in parsed if "name server" in k]
        for key in ns_keys:
            ns = parsed[key]
            if isinstance(ns, list):
                for n in ns:
                    relationships.append({"type": "has_dns_record", "from": target, "to": n, "record_type": "NS"})
            elif isinstance(ns, str):
                relationships.append({"type": "has_dns_record", "from": target, "to": ns, "record_type": "NS"})

        return relationships

    async def health_check(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "whois", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            return True
        except Exception:
            return False
