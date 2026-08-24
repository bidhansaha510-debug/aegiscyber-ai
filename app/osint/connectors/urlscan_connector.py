from __future__ import annotations

from typing import Any

import httpx

from app.osint.connectors.base import BaseOSINTConnector
from app.osint.models import OSINTResult, EntityType
from app.logging_config import get_logger

logger = get_logger("osint.connectors.urlscan")


class URLScanConnector(BaseOSINTConnector):
    CONNECTOR_NAME = "urlscan"
    SUPPORTED_ENTITIES = [EntityType.DOMAIN, EntityType.URL, EntityType.IP]
    API_URL = "https://urlscan.io/api/v1"

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    async def search(self, entity_type: EntityType, value: str, **kwargs: Any) -> list[OSINTResult]:
        results: list[OSINTResult] = []
        headers = {}
        if self._api_key:
            headers["API-Key"] = self._api_key

        try:
            query = f"domain:{value}" if entity_type == EntityType.DOMAIN else f"page.url:{value}"
            if entity_type == EntityType.IP:
                query = f"page.ip:{value}"

            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                response = await client.get(
                    f"{self.API_URL}/search/?q={query}&size=20"
                )
                if response.status_code == 200:
                    data = response.json()
                    for scan in data.get("results", []):
                        page = scan.get("page", {})
                        results.append(OSINTResult(
                            source="urlscan.io",
                            entity_type="url",
                            value=page.get("url", ""),
                            confidence=0.85,
                            evidence=f"urlscan.io scan result for {value}",
                            raw_data={
                                "domain": page.get("domain", ""),
                                "ip": page.get("ip", ""),
                                "country": page.get("country", ""),
                                "server": page.get("server", ""),
                                "status": page.get("status", ""),
                                "title": page.get("title", ""),
                                "scan_id": scan.get("_id", ""),
                            },
                            relationships=[
                                {"type": "resolves_to", "from": page.get("domain", ""), "to": page.get("ip", "")},
                            ] if page.get("ip") else [],
                        ))
        except Exception as e:
            logger.error("urlscan.io search failed for %s: %s", value, e)

        return results

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.API_URL}/search/?q=domain:example.com&size=1")
                return response.status_code == 200
        except Exception:
            return False
