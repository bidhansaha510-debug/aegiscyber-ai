from __future__ import annotations

import asyncio
import time
from typing import Any

from app.osint.connectors.base import BaseOSINTConnector
from app.osint.connectors.dns_connector import DNSConnector
from app.osint.connectors.whois_connector import WhoisConnector
from app.osint.connectors.crt_connector import CRTConnector
from app.osint.connectors.github_connector import GitHubConnector
from app.osint.connectors.urlscan_connector import URLScanConnector
from app.osint.connectors.shodan_connector import ShodanConnector
from app.osint.models import (
    EntityType,
    OSINTEntity,
    OSINTRelationship,
    OSINTResult,
    OSINTSearchRequest,
    OSINTSearchResponse,
    RelationshipType,
)
from app.osint.normalization import normalize_result, deduplicate_entities, normalize_entity_type
from app.osint.graph import KnowledgeGraph
from app.logging_config import get_logger

logger = get_logger("osint.engine")

RELATIONSHIP_TYPE_MAP = {
    "has_subdomain": RelationshipType.HAS_SUBDOMAIN,
    "resolves_to": RelationshipType.RESOLVES_TO,
    "has_email": RelationshipType.HAS_EMAIL,
    "has_username": RelationshipType.HAS_USERNAME,
    "owns_domain": RelationshipType.OWNS_DOMAIN,
    "has_certificate": RelationshipType.HAS_CERTIFICATE,
    "has_dns_record": RelationshipType.HAS_DNS_RECORD,
    "associated_with": RelationshipType.ASSOCIATED_WITH,
    "registered_by": RelationshipType.REGISTERED_BY,
    "linked_to": RelationshipType.LINKED_TO,
    "hosted_on": RelationshipType.HOSTED_ON,
    "uses_technology": RelationshipType.USES_TECHNOLOGY,
}


class OSINTEngine:
    def __init__(self, graph: KnowledgeGraph | None = None, secrets_manager: Any = None) -> None:
        self._connectors: dict[str, BaseOSINTConnector] = {}
        self._graph = graph or KnowledgeGraph()
        self._secrets = secrets_manager
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register_connector(DNSConnector())
        self.register_connector(WhoisConnector())
        self.register_connector(CRTConnector())
        self.register_connector(GitHubConnector(secrets_manager=self._secrets))
        self.register_connector(URLScanConnector(secrets_manager=self._secrets))
        self.register_connector(ShodanConnector(secrets_manager=self._secrets))

    def register_connector(self, connector: BaseOSINTConnector) -> None:
        self._connectors[connector.CONNECTOR_NAME] = connector
        logger.debug("OSINT connector registered: %s", connector.CONNECTOR_NAME)

    def get_connector(self, name: str) -> BaseOSINTConnector | None:
        return self._connectors.get(name)

    @property
    def graph(self) -> KnowledgeGraph:
        return self._graph

    async def search(self, request: OSINTSearchRequest) -> OSINTSearchResponse:
        start_time = time.monotonic()
        response = OSINTSearchResponse()

        connectors_to_use = self._select_connectors(request)
        response.connectors_used = [c.CONNECTOR_NAME for c in connectors_to_use]

        tasks = []
        for connector in connectors_to_use:
            tasks.append(self._run_connector(connector, request.target_type, request.target_value))

        results_per_connector = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: list[OSINTResult] = []
        for result in results_per_connector:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                response.errors.append(str(result))

        response.results = all_results

        entities = [normalize_result(r) for r in all_results]
        entities = deduplicate_entities(entities)

        for entity in entities:
            entity.investigation_id = request.investigation_id
            self._graph.add_entity(entity)
        response.entities_found = len(entities)

        rel_count = 0
        for result in all_results:
            for rel_data in result.relationships:
                rel_count += self._process_relationship(rel_data, result.source)
        response.relationships_found = rel_count

        response.duration_seconds = round(time.monotonic() - start_time, 3)

        logger.info(
            "OSINT search for %s:%s complete: %d entities, %d relationships in %.1fs",
            request.target_type.value,
            request.target_value,
            response.entities_found,
            response.relationships_found,
            response.duration_seconds,
        )

        return response

    def _select_connectors(self, request: OSINTSearchRequest) -> list[BaseOSINTConnector]:
        if request.connectors:
            return [
                self._connectors[name]
                for name in request.connectors
                if name in self._connectors
            ]

        return [
            c for c in self._connectors.values()
            if c.supports_entity(request.target_type)
        ]

    async def _run_connector(
        self,
        connector: BaseOSINTConnector,
        entity_type: EntityType,
        value: str,
    ) -> list[OSINTResult]:
        try:
            return await asyncio.wait_for(
                connector.search(entity_type, value),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            logger.warning("Connector %s timed out for %s", connector.CONNECTOR_NAME, value)
            return []
        except Exception as e:
            logger.error("Connector %s error: %s", connector.CONNECTOR_NAME, e)
            return []

    def _process_relationship(self, rel_data: dict[str, Any], source: str) -> int:
        rel_type_str = rel_data.get("type", "associated_with")
        rel_type = RELATIONSHIP_TYPE_MAP.get(rel_type_str, RelationshipType.ASSOCIATED_WITH)

        from_value = rel_data.get("from", "")
        to_value = rel_data.get("to", "")
        if not from_value or not to_value:
            return 0

        from_type = self._infer_entity_type(from_value)
        to_type = self._infer_entity_type(to_value)

        from_entity = self._graph.find_entity(from_type, from_value)
        if not from_entity:
            from_entity = OSINTEntity(entity_type=from_type, value=from_value, source=source, confidence=0.5)
            self._graph.add_entity(from_entity)

        to_entity = self._graph.find_entity(to_type, to_value)
        if not to_entity:
            to_entity = OSINTEntity(entity_type=to_type, value=to_value, source=source, confidence=0.5)
            self._graph.add_entity(to_entity)

        relationship = OSINTRelationship(
            source_entity_id=from_entity.id,
            target_entity_id=to_entity.id,
            relationship_type=rel_type,
            source=source,
            confidence=0.7,
        )
        self._graph.add_relationship(relationship)
        return 1

    def _infer_entity_type(self, value: str) -> EntityType:
        import re
        value = value.strip()

        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
            return EntityType.IP

        if re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value):
            return EntityType.EMAIL

        if value.startswith("http://") or value.startswith("https://"):
            return EntityType.URL

        if "." in value and not value.startswith("/"):
            return EntityType.DOMAIN

        return EntityType.DOMAIN

    async def health_check_all(self) -> dict[str, bool]:
        results = {}
        for name, connector in self._connectors.items():
            try:
                results[name] = await asyncio.wait_for(connector.health_check(), timeout=10.0)
            except Exception:
                results[name] = False
        return results

    def get_connectors(self) -> list[str]:
        return list(self._connectors.keys())
