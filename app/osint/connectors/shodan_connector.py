from __future__ import annotations

import os
from typing import Any

import httpx

from app.osint.connectors.base import BaseOSINTConnector
from app.osint.models import OSINTResult, EntityType
from app.logging_config import get_logger

logger = get_logger("osint.connectors.shodan")


class ShodanConnector(BaseOSINTConnector):
    CONNECTOR_NAME = "shodan"
    SUPPORTED_ENTITIES = [EntityType.IP, EntityType.DOMAIN]
    API_URL = "https://api.shodan.io"

    def __init__(self, api_key: str = "", secrets_manager: Any = None) -> None:
        self._secrets = secrets_manager
        self._api_key = api_key
        if not self._api_key and self._secrets:
            self._api_key = self._secrets.get_secret("shodan_api_key") or ""
        if not self._api_key:
            self._api_key = os.environ.get("SHODAN_API_KEY", "")

    async def search(self, entity_type: EntityType, value: str, **kwargs: Any) -> list[OSINTResult]:
        if not self._api_key and self._secrets:
            self._api_key = self._secrets.get_secret("shodan_api_key") or ""
        if not self._api_key:
            self._api_key = os.environ.get("SHODAN_API_KEY", "")

        if not self._api_key:
            logger.warning("Shodan API key not configured, skipping")
            return []

        results: list[OSINTResult] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if entity_type == EntityType.IP:
                    response = await client.get(
                        f"{self.API_URL}/shodan/host/{value}?key={self._api_key}"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        results.append(OSINTResult(
                            source="shodan",
                            entity_type="ip",
                            value=value,
                            confidence=0.9,
                            evidence=f"Shodan host data for {value}",
                            raw_data={
                                "os": data.get("os", ""),
                                "ports": data.get("ports", []),
                                "hostnames": data.get("hostnames", []),
                                "org": data.get("org", ""),
                                "isp": data.get("isp", ""),
                                "country": data.get("country_name", ""),
                                "city": data.get("city", ""),
                                "vulns": data.get("vulns", []),
                            },
                        ))

                        for hostname in data.get("hostnames", []):
                            results.append(OSINTResult(
                                source="shodan",
                                entity_type="domain",
                                value=hostname,
                                confidence=0.85,
                                evidence=f"Hostname from Shodan for {value}",
                                relationships=[{"type": "resolves_to", "from": hostname, "to": value}],
                            ))

                elif entity_type == EntityType.DOMAIN:
                    response = await client.get(
                        f"{self.API_URL}/dns/resolve?hostnames={value}&key={self._api_key}"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        ip = data.get(value, "")
                        if ip:
                            results.append(OSINTResult(
                                source="shodan",
                                entity_type="ip",
                                value=ip,
                                confidence=0.9,
                                evidence=f"Shodan DNS resolution for {value}",
                                relationships=[{"type": "resolves_to", "from": value, "to": ip}],
                            ))

        except Exception as e:
            logger.error("Shodan search failed for %s: %s", value, e)

        return results

    async def health_check(self) -> bool:
        if not self._api_key and self._secrets:
            self._api_key = self._secrets.get_secret("shodan_api_key") or ""
        if not self._api_key:
            self._api_key = os.environ.get("SHODAN_API_KEY", "")

        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.API_URL}/api-info?key={self._api_key}")
                return response.status_code == 200
        except Exception:
            return False
