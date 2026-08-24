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
    API_URL = "https://crt.sh/?q={domain}&output=json"

    async def search(self, entity_type: EntityType, value: str, **kwargs: Any) -> list[OSINTResult]:
        results: list[OSINTResult] = []

        try:
            async with httpx.AsyncClient(timeout=30.0, verify=True) as client:
                url = self.API_URL.format(domain=value)
                response = await client.get(url)

                if response.status_code == 200:
                    certs = response.json()
                    seen_names: set[str] = set()

                    for cert in certs:
                        common_name = cert.get("common_name", "")
                        name_value = cert.get("name_value", "")

                        names = set()
                        if common_name:
                            names.add(common_name.lower())
                        for name in name_value.split("\n"):
                            name = name.strip().lower()
                            if name and name not in seen_names:
                                names.add(name)

                        for name in names:
                            if name in seen_names:
                                continue
                            seen_names.add(name)

                            results.append(OSINTResult(
                                source="crt.sh",
                                entity_type="subdomain" if name != value.lower() else "domain",
                                value=name,
                                confidence=0.95,
                                evidence=f"Certificate transparency log for {value}",
                                raw_data={
                                    "issuer": cert.get("issuer_name", ""),
                                    "not_before": cert.get("not_before", ""),
                                    "not_after": cert.get("not_after", ""),
                                    "serial_number": cert.get("serial_number", ""),
                                },
                                relationships=[{
                                    "type": "has_certificate" if name == value.lower() else "has_subdomain",
                                    "from": value,
                                    "to": name,
                                }],
                            ))

                    logger.info("crt.sh found %d unique names for %s", len(seen_names), value)
                else:
                    logger.warning("crt.sh returned status %d for %s", response.status_code, value)

        except Exception as e:
            logger.error("crt.sh lookup failed for %s: %s", value, e)

        return results

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://crt.sh/?q=example.com&output=json")
                return response.status_code == 200
        except Exception:
            return False
