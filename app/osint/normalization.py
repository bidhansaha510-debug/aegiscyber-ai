from __future__ import annotations

from app.osint.models import OSINTResult, OSINTEntity, EntityType
from app.logging_config import get_logger

logger = get_logger("osint.normalization")

ENTITY_TYPE_MAP = {
    "domain": EntityType.DOMAIN,
    "subdomain": EntityType.SUBDOMAIN,
    "ip": EntityType.IP,
    "ip_address": EntityType.IP,
    "email": EntityType.EMAIL,
    "username": EntityType.USERNAME,
    "url": EntityType.URL,
    "certificate": EntityType.CERTIFICATE,
    "organization": EntityType.ORGANIZATION,
    "person": EntityType.PERSON,
    "document": EntityType.DOCUMENT,
    "technology": EntityType.TECHNOLOGY,
    "hostname": EntityType.DOMAIN,
    "dns_record": EntityType.DOMAIN,
    "service": EntityType.SERVICE,
    "port": EntityType.PORT,
    "asn": EntityType.ASN,
    "hash": EntityType.HASH,
}


def normalize_entity_type(raw_type: str) -> EntityType:
    return ENTITY_TYPE_MAP.get(raw_type.lower().strip(), EntityType.DOMAIN)


def normalize_result(result: OSINTResult) -> OSINTEntity:
    entity_type = normalize_entity_type(result.entity_type)

    value = result.value.strip().lower()
    if entity_type == EntityType.DOMAIN or entity_type == EntityType.SUBDOMAIN:
        value = value.rstrip(".")
    if entity_type == EntityType.EMAIL:
        value = value.lower()
    if entity_type == EntityType.URL:
        value = result.value.strip()

    return OSINTEntity(
        entity_type=entity_type,
        value=value,
        confidence=max(0.0, min(1.0, result.confidence)),
        source=result.source,
        metadata={
            "evidence": result.evidence,
            "raw_data": result.raw_data,
        },
    )


def deduplicate_entities(entities: list[OSINTEntity]) -> list[OSINTEntity]:
    seen: dict[str, OSINTEntity] = {}
    for entity in entities:
        key = f"{entity.entity_type.value}:{entity.value}"
        if key in seen:
            existing = seen[key]
            if entity.confidence > existing.confidence:
                existing.confidence = entity.confidence
            existing.metadata.update(entity.metadata)
            sources = set()
            if existing.source:
                sources.add(existing.source)
            if entity.source:
                sources.add(entity.source)
            existing.source = ", ".join(sorted(sources))
        else:
            seen[key] = entity
    return list(seen.values())
