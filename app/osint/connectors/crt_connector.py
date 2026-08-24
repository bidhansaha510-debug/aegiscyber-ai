from __future__ import annotations

from typing import Any

import httpx

from app.osint.connectors.base import BaseOSINTConnector
from app.osint.models import OSINTResult, EntityType
from app.logging_config import get_logger

logger = get_logger("osint.connectors.crt")


class CRTConnector(BaseOSINTConnector):
    CONNECTOR_NAME = "crt"
    SUPPORTED_ENTITIES = [EntityType.DOMAIN]

    async def search(self, entity_type: EntityType, value: str, **kwargs: Any) -> list[OSINTResult]:
        results: list[OSINTResult] = []
        seen_names: set[str] = set()

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                try:
                    response = await client.get(f"https://crt.sh/?q=%.{value}&output=json")
                    if response.status_code == 200:
                        data = response.json()
                        for cert in data:
                            name_val = cert.get("name_value", "")
                            for name in name_val.split("\n"):
                                name = name.strip().lower()
                                if name.startswith("*."):
                                    name = name[2:]
                                if name and name not in seen_names:
                                    seen_names.add(name)
                                    results.append(OSINTResult(
                                        source="crt.sh",
                                        entity_type="domain",
                                        value=name,
                                        confidence=0.9,
                                        evidence=f"Certificate transparency log for {value}",
                                        relationships=[{
                                            "type": "has_certificate" if name == value.lower() else "has_subdomain",
                                            "from": value,
                                            "to": name,
                                        }],
                                    ))
                except Exception:
                    pass

                if not results:
                    try:
                        cs_url = f"https://api.certspotter.com/v1/issuances?domain={value}&include_subdomains=true&expand=dns_names"
                        cs_resp = await client.get(cs_url)
                        if cs_resp.status_code == 200:
                            data = cs_resp.json()
                            for item in data:
                                for name in item.get("dns_names", []):
                                    name = name.strip().lower()
                                    if name.startswith("*."):
                                        name = name[2:]
                                    if name and name not in seen_names:
                                        seen_names.add(name)
                                        results.append(OSINTResult(
                                            source="certspotter",
                                            entity_type="domain",
                                            value=name,
                                            confidence=0.9,
                                            evidence=f"CertSpotter CT log for {value}",
                                            relationships=[{
                                                "type": "has_certificate" if name == value.lower() else "has_subdomain",
                                                "from": value,
                                                "to": name,
                                            }],
                                        ))
                    except Exception as e:
                        logger.debug("CertSpotter fallback error: %s", e)

        except Exception as e:
            logger.error("Certificate transparency lookup failed for %s: %s", value, e)

        return results

    async def health_check(self) -> bool:
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                resp = await client.get("https://api.certspotter.com/v1/issuances?domain=example.com&include_subdomains=false")
                return resp.status_code in (200, 429)
        except Exception:
            return False
