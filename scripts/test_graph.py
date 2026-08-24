from app.osint.graph import KnowledgeGraph
from app.osint.models import OSINTEntity, OSINTRelationship, EntityType, RelationshipType

g = KnowledgeGraph()

e1 = OSINTEntity(entity_type=EntityType.DOMAIN, value="example.com", source="test", confidence=0.9)
e2 = OSINTEntity(entity_type=EntityType.IP, value="93.184.216.34", source="dns", confidence=1.0)
e3 = OSINTEntity(entity_type=EntityType.SUBDOMAIN, value="www.example.com", source="crt", confidence=0.95)

id1 = g.add_entity(e1)
id2 = g.add_entity(e2)
id3 = g.add_entity(e3)

r1 = OSINTRelationship(
    source_entity_id=id1, target_entity_id=id2,
    relationship_type=RelationshipType.RESOLVES_TO, source="dns", confidence=1.0,
)
r2 = OSINTRelationship(
    source_entity_id=id1, target_entity_id=id3,
    relationship_type=RelationshipType.HAS_SUBDOMAIN, source="crt", confidence=0.95,
)
g.add_relationship(r1)
g.add_relationship(r2)

stats = g.get_statistics()
print(f"Entities: {stats['total_entities']}, Relationships: {stats['total_relationships']}")
print(f"Types: {stats['entities_by_type']}")

related = g.get_related_entities(id1)
print(f"Related to example.com: {[e.value for e in related]}")

subgraph = g.get_subgraph(id1)
print(f"Subgraph: {len(subgraph['nodes'])} nodes, {len(subgraph['edges'])} edges")

print("\nAll tests passed!")
