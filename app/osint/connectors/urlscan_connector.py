from __future__ import annotations

import os
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

    def __init__(self, api_key: str = "", secrets_manager: Any = None) -> None:
        self._secrets = secrets_manager
        self._api_key = api_key
        if not self._api_key and self._secrets:
            self._api_key = self._secrets.get_secret("urlscan_api_key") or ""
        if not self._api_key:
            self._api_key = os.environ.get("URLSCAN_API_KEY", "")

    async def search(self, entity_type: EntityType, value: str, **kwargs: Any) -> list[OSINTResult]:
        if not self._api_key and self._secrets:
            self._api_key = self._secrets.get_secret("urlscan_api_key") or ""
        if not self._api_key:
            self._api_key = os.environ.get("URLSCAN_API_KEY", "")

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
                    for item in data.get("results", []):
                        page = item.get("page", {})
                        page_domain = page.get("domain", "")
                        page_ip = page.get("ip", "")
                        page_url = page.get("url", "")
                        page_server = page.get("server", "")

                        if page_domain and page_domain != value:
                            results.append(OSINTResult(
                                source="urlscan",
                                entity_type="domain",
                                value=page_domain,
                                confidence=0.8,
                                evidence=f"Domain associated with {value} on URLScan",
                                relationships=[{"type": "associated_with", "from": value, "to": page_domain}],
                            ))

                        if page_ip:
                            results.append(OSINTResult(
                                source="urlscan",
                                entity_type="ip",
                                value=page_ip,
                                confidence=0.85,
                                evidence=f"IP hosting {value} on URLScan",
                                relationships=[{"type": "hosted_on", "from": value, "to": page_ip}],
                            ))

                        if page_server:
                            results.append(OSINTResult(
                                source="urlscan",
                                entity_type="technology",
                                value=page_server,
                                confidence=0.75,
                                evidence=f"Web server for {value}: {page_server}",
                                relationships=[{"type": "uses_technology", "from": value, "to": page_server}],
                            ))

        except Exception as e:
            logger.error("URLScan search failed for %s: %s", value, e)

        return results

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.API_URL}/search/?q=domain:example.com&size=1")
                return response.status_code == 200
        except Exception:
            return False
