from __future__ import annotations

from typing import Any

import networkx as nx

from app.osint.models import OSINTEntity, OSINTRelationship, EntityType, RelationshipType
from app.logging_config import get_logger

logger = get_logger("osint.graph")


class KnowledgeGraph:
    def __init__(self) -> None:
        self._graph = nx.DiGraph()
        self._entities: dict[str, OSINTEntity] = {}
        self._relationships: list[OSINTRelationship] = []

    def add_entity(self, entity: OSINTEntity) -> str:
        existing = self.find_entity(entity.entity_type, entity.value)
        if existing:
            if entity.confidence > existing.confidence:
                existing.confidence = entity.confidence
            existing.last_seen = entity.last_seen
            existing.metadata.update(entity.metadata)
            self._graph.nodes[existing.id].update(entity.metadata)
            return existing.id

        self._entities[entity.id] = entity
        self._graph.add_node(
            entity.id,
            entity_type=entity.entity_type.value,
            value=entity.value,
            confidence=entity.confidence,
            source=entity.source,
        )
        return entity.id

    def add_relationship(self, relationship: OSINTRelationship) -> str:
        if relationship.source_entity_id not in self._entities:
            logger.warning("Source entity %s not found", relationship.source_entity_id)
            return ""
        if relationship.target_entity_id not in self._entities:
            logger.warning("Target entity %s not found", relationship.target_entity_id)
            return ""

        self._relationships.append(relationship)
        self._graph.add_edge(
            relationship.source_entity_id,
            relationship.target_entity_id,
            relationship_type=relationship.relationship_type.value,
            confidence=relationship.confidence,
            source=relationship.source,
        )
        return relationship.id

    def find_entity(self, entity_type: EntityType, value: str) -> OSINTEntity | None:
        for entity in self._entities.values():
            if entity.entity_type == entity_type and entity.value.lower() == value.lower():
                return entity
        return None

    def get_entity(self, entity_id: str) -> OSINTEntity | None:
        return self._entities.get(entity_id)

    def get_entities_by_type(self, entity_type: EntityType) -> list[OSINTEntity]:
        return [e for e in self._entities.values() if e.entity_type == entity_type]

    def get_related_entities(self, entity_id: str, depth: int = 1) -> list[OSINTEntity]:
        if entity_id not in self._graph:
            return []

        related_ids = set()
        current_layer = {entity_id}

        for _ in range(depth):
            next_layer = set()
            for node_id in current_layer:
                next_layer.update(self._graph.successors(node_id))
                next_layer.update(self._graph.predecessors(node_id))
            next_layer -= related_ids
            next_layer.discard(entity_id)
            related_ids.update(next_layer)
            current_layer = next_layer

        return [self._entities[eid] for eid in related_ids if eid in self._entities]

    def get_relationships_for(self, entity_id: str) -> list[OSINTRelationship]:
        return [
            r for r in self._relationships
            if r.source_entity_id == entity_id or r.target_entity_id == entity_id
        ]

    def query_path(self, from_id: str, to_id: str) -> list[str]:
        try:
            path = nx.shortest_path(self._graph, from_id, to_id)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_subgraph(self, entity_id: str, depth: int = 2) -> dict[str, Any]:
        related = self.get_related_entities(entity_id, depth)
        all_ids = {entity_id} | {e.id for e in related}

        nodes = []
        for eid in all_ids:
            entity = self._entities.get(eid)
            if entity:
                nodes.append({
                    "id": entity.id,
                    "type": entity.entity_type.value,
                    "value": entity.value,
                    "confidence": entity.confidence,
                })

        edges = []
        for rel in self._relationships:
            if rel.source_entity_id in all_ids and rel.target_entity_id in all_ids:
                edges.append({
                    "source": rel.source_entity_id,
                    "target": rel.target_entity_id,
                    "type": rel.relationship_type.value,
                    "confidence": rel.confidence,
                })

        return {"nodes": nodes, "edges": edges}

    def search_entities(self, query: str) -> list[OSINTEntity]:
        query_lower = query.lower()
        return [
            e for e in self._entities.values()
            if query_lower in e.value.lower() or query_lower in str(e.metadata).lower()
        ]

    def get_statistics(self) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for entity in self._entities.values():
            t = entity.entity_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        rel_counts: dict[str, int] = {}
        for rel in self._relationships:
            t = rel.relationship_type.value
            rel_counts[t] = rel_counts.get(t, 0) + 1

        return {
            "total_entities": len(self._entities),
            "total_relationships": len(self._relationships),
            "entities_by_type": type_counts,
            "relationships_by_type": rel_counts,
            "graph_nodes": self._graph.number_of_nodes(),
            "graph_edges": self._graph.number_of_edges(),
        }

    def export_to_dict(self) -> dict[str, Any]:
        return {
            "entities": [e.model_dump() for e in self._entities.values()],
            "relationships": [r.model_dump() for r in self._relationships],
        }

    def clear(self) -> None:
        self._graph.clear()
        self._entities.clear()
        self._relationships.clear()
