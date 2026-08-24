from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.osint.models import OSINTResult, EntityType


class BaseOSINTConnector(ABC):
    CONNECTOR_NAME: str = "base"
    SUPPORTED_ENTITIES: list[EntityType] = []

    @abstractmethod
    async def search(self, entity_type: EntityType, value: str, **kwargs: Any) -> list[OSINTResult]:
        ...

    async def normalize(self, raw_data: dict[str, Any]) -> list[OSINTResult]:
        return []

    async def health_check(self) -> bool:
        return True

    def supports_entity(self, entity_type: EntityType) -> bool:
        return entity_type in self.SUPPORTED_ENTITIES
