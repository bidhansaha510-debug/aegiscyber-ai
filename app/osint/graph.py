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

    def get_entity_count(self) -> int:
        return len(self._entities)

    def get_all_entities(self) -> list[OSINTEntity]:
        return list(self._entities.values())

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

    def get_entity_neighbors(self, entity_id: str, max_depth: int = 1) -> list[dict[str, Any]]:
        if entity_id not in self._entities:
            return []

        neighbors: list[dict[str, Any]] = []
        visited = {entity_id}
        queue = [(entity_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for successor in self._graph.successors(current_id):
                if successor not in visited:
                    visited.add(successor)
                    queue.append((successor, depth + 1))
                    edge_data = self._graph.get_edge_data(current_id, successor)
                    target_entity = self._entities.get(successor)
                    if target_entity:
                        neighbors.append({
                            "entity": target_entity.model_dump(),
                            "relationship": edge_data.get("relationship_type", ""),
                            "direction": "outgoing",
                            "depth": depth + 1,
                        })

            for predecessor in self._graph.predecessors(current_id):
                if predecessor not in visited:
                    visited.add(predecessor)
                    queue.append((predecessor, depth + 1))
                    edge_data = self._graph.get_edge_data(predecessor, current_id)
                    source_entity = self._entities.get(predecessor)
                    if source_entity:
                        neighbors.append({
                            "entity": source_entity.model_dump(),
                            "relationship": edge_data.get("relationship_type", ""),
                            "direction": "incoming",
                            "depth": depth + 1,
                        })

        return neighbors

    def get_subgraph(self, center_entity_id: str, depth: int = 2) -> dict[str, Any]:
        if center_entity_id not in self._entities:
            return {"nodes": [], "edges": []}

        nodes = []
        visited = {center_entity_id}
        queue = [(center_entity_id, 0)]

        while queue:
            current_id, current_depth = queue.pop(0)
            entity = self._entities.get(current_id)
            if entity:
                nodes.append(entity.model_dump())

            if current_depth >= depth:
                continue

            all_neighbors = list(self._graph.successors(current_id)) + list(self._graph.predecessors(current_id))
            for neighbor in all_neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, current_depth + 1))

        all_ids = {n["id"] for n in nodes}
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
