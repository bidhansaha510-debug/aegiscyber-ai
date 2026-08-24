from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class EntityType(str, enum.Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    DOMAIN = "domain"
    IP = "ip"
    EMAIL = "email"
    USERNAME = "username"
    URL = "url"
    CERTIFICATE = "certificate"
    DOCUMENT = "document"
    TECHNOLOGY = "technology"
    SUBDOMAIN = "subdomain"
    PORT = "port"
    SERVICE = "service"
    ASN = "asn"
    HASH = "hash"


class RelationshipType(str, enum.Enum):
    HAS_SUBDOMAIN = "has_subdomain"
    RESOLVES_TO = "resolves_to"
    HAS_EMAIL = "has_email"
    HAS_USERNAME = "has_username"
    OWNS_DOMAIN = "owns_domain"
    RUNS_SERVICE = "runs_service"
    HAS_PORT = "has_port"
    HAS_CERTIFICATE = "has_certificate"
    USES_TECHNOLOGY = "uses_technology"
    HAS_DNS_RECORD = "has_dns_record"
    BELONGS_TO_ASN = "belongs_to_asn"
    ASSOCIATED_WITH = "associated_with"
    HOSTED_ON = "hosted_on"
    REGISTERED_BY = "registered_by"
    CONTAINS = "contains"
    LINKED_TO = "linked_to"


class OSINTEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    entity_type: EntityType
    value: str
    confidence: float = 0.0
    source: str = ""
    first_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)
    investigation_id: str = ""
    tags: list[str] = Field(default_factory=list)


class OSINTRelationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    confidence: float = 0.0
    source: str = ""
    discovered_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class OSINTResult(BaseModel):
    source: str
    entity_type: str
    value: str
    confidence: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence: str = ""
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    raw_data: dict[str, Any] = Field(default_factory=dict)


class OSINTSearchRequest(BaseModel):
    target_type: EntityType
    target_value: str
    connectors: list[str] = Field(default_factory=list)
    investigation_id: str = ""
    max_depth: int = 1
    passive_only: bool = True


class OSINTSearchResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    results: list[OSINTResult] = Field(default_factory=list)
    entities_found: int = 0
    relationships_found: int = 0
    connectors_used: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
