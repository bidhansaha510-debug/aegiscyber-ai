from __future__ import annotations

import asyncio
import re
import socket
from typing import Any

from app.osint.connectors.base import BaseOSINTConnector
from app.osint.models import OSINTResult, EntityType
from app.logging_config import get_logger

logger = get_logger("osint.connectors.whois")


class WhoisConnector(BaseOSINTConnector):
    CONNECTOR_NAME = "whois"
    SUPPORTED_ENTITIES = [EntityType.DOMAIN, EntityType.IP]

    def _query_whois_socket(self, target: str, server: str = "whois.iana.org") -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(8.0)
            s.connect((server, 43))
            s.send((target.strip() + "\r\n").encode("utf-8"))
            response = b""
            while True:
                data = s.recv(4096)
                if not data:
                    break
                response += data
            s.close()
            text = response.decode("utf-8", errors="replace")

            refer_match = re.search(r"refer:\s*([^\s]+)", text, re.IGNORECASE) or re.search(r"whois server:\s*([^\s]+)", text, re.IGNORECASE)
            if refer_match and server == "whois.iana.org":
                refer_server = refer_match.group(1).strip()
                if refer_server and refer_server != server:
                    return self._query_whois_socket(target, refer_server)

            return text
        except Exception as e:
            logger.debug("Socket WHOIS error for %s on %s: %s", target, server, e)
            return ""

    async def search(self, entity_type: EntityType, value: str, **kwargs: Any) -> list[OSINTResult]:
        loop = asyncio.get_running_loop()
        raw_output = await loop.run_in_executor(None, self._query_whois_socket, value)

        if not raw_output:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "whois", value,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
                raw_output = stdout.decode("utf-8", errors="replace")
            except Exception:
                pass

        if not raw_output:
            return []

        parsed = self._parse_whois(raw_output)
        relationships = self._extract_relationships(value, parsed)

        return [OSINTResult(
            source="whois",
            entity_type=entity_type.value,
            value=value,
            confidence=0.9,
            evidence=f"WHOIS data for {value}",
            raw_data=parsed,
            relationships=relationships,
        )]

    def _parse_whois(self, text: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for line in text.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("%") and not line.startswith("#"):
                key, val = line.split(":", 1)
                key = key.strip().lower()
                val = val.strip()
                if val:
                    if key in result:
                        if isinstance(result[key], list):
                            result[key].append(val)
                        else:
                            result[key] = [result[key], val]
                    else:
                        result[key] = val
        return result

    def _extract_relationships(self, target: str, parsed: dict[str, Any]) -> list[dict[str, Any]]:
        relationships = []

        registrar = parsed.get("registrar", "")
        if registrar:
            relationships.append({
                "type": "registered_by",
                "from": target,
                "to": registrar if isinstance(registrar, str) else registrar[0],
            })

        ns_keys = [k for k in parsed if "name server" in k or "nserver" in k]
        for key in ns_keys:
            ns = parsed[key]
            if isinstance(ns, list):
                for n in ns:
                    relationships.append({"type": "has_dns_record", "from": target, "to": n, "record_type": "NS"})
            elif isinstance(ns, str):
                relationships.append({"type": "has_dns_record", "from": target, "to": ns, "record_type": "NS"})

        return relationships

    async def health_check(self) -> bool:
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, self._query_whois_socket, "iana.org")
        return bool(res)
