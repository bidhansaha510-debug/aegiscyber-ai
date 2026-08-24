from __future__ import annotations

from .models import OSINTEntity, OSINTRelationship, OSINTResult, OSINTSearchRequest, OSINTSearchResponse, EntityType, RelationshipType
from .engine import OSINTEngine
from .graph import KnowledgeGraph
from .normalization import normalize_result, deduplicate_entities

__all__ = [
    "OSINTEntity", "OSINTRelationship", "OSINTResult",
    "OSINTSearchRequest", "OSINTSearchResponse",
    "EntityType", "RelationshipType",
    "OSINTEngine", "KnowledgeGraph",
    "normalize_result", "deduplicate_entities",
]
