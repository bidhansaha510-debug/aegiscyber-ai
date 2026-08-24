from __future__ import annotations

import enum
import ipaddress
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.logging_config import get_logger

logger = get_logger("security.authorization")


class AuthorizationState(str, enum.Enum):
    UNCONFIRMED = "unconfirmed"
    SCOPE_DEFINED = "scope_defined"
    USER_CONFIRMED = "user_confirmed"
    ACTIVE = "active"
    REVOKED = "revoked"


class ScopeType(str, enum.Enum):
    IP_ADDRESS = "ip_address"
    IP_RANGE = "ip_range"
    DOMAIN = "domain"
    HOSTNAME = "hostname"
    URL = "url"
    WILDCARD_DOMAIN = "wildcard_domain"


class ScopeEntry(BaseModel):
    scope_type: ScopeType
    value: str
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


class TargetScope(BaseModel):
    entries: list[ScopeEntry] = Field(default_factory=list)
    state: AuthorizationState = AuthorizationState.UNCONFIRMED
    confirmed_at: datetime | None = None
    confirmed_by: str = "user"
    passive_only: bool = False

    def add_entry(self, scope_type: ScopeType, value: str, notes: str = "") -> None:
        entry = ScopeEntry(scope_type=scope_type, value=value, notes=notes)
        self.entries.append(entry)
        if self.state == AuthorizationState.UNCONFIRMED:
            self.state = AuthorizationState.SCOPE_DEFINED
        logger.info("Scope entry added: %s = %s", scope_type.value, value)

    def remove_entry(self, value: str) -> bool:
        original_length = len(self.entries)
        self.entries = [e for e in self.entries if e.value != value]
        removed = len(self.entries) < original_length
        if removed:
            logger.info("Scope entry removed: %s", value)
        return removed

    def confirm(self) -> None:
        if not self.entries:
            raise ValueError("Cannot confirm empty scope")
        self.state = AuthorizationState.USER_CONFIRMED
        self.confirmed_at = datetime.now(timezone.utc)
        logger.info("Scope confirmed with %d entries", len(self.entries))

    def activate(self) -> None:
        if self.state != AuthorizationState.USER_CONFIRMED:
            raise ValueError("Scope must be confirmed before activation")
        self.state = AuthorizationState.ACTIVE
        logger.info("Scope activated")

    def revoke(self) -> None:
        self.state = AuthorizationState.REVOKED
        logger.info("Scope revoked")

    def is_target_authorized(self, target: str) -> bool:
        if self.state not in (AuthorizationState.USER_CONFIRMED, AuthorizationState.ACTIVE):
            return False

        for entry in self.entries:
            if self._matches_entry(entry, target):
                return True
        return False

    def _matches_entry(self, entry: ScopeEntry, target: str) -> bool:
        target_lower = target.lower().strip()
        value_lower = entry.value.lower().strip()

        if entry.scope_type == ScopeType.IP_ADDRESS:
            return target_lower == value_lower

        if entry.scope_type == ScopeType.IP_RANGE:
            try:
                network = ipaddress.ip_network(entry.value, strict=False)
                target_ip = ipaddress.ip_address(target)
                return target_ip in network
            except ValueError:
                return False

        if entry.scope_type == ScopeType.DOMAIN:
            return target_lower == value_lower or target_lower.endswith(f".{value_lower}")

        if entry.scope_type == ScopeType.HOSTNAME:
            return target_lower == value_lower

        if entry.scope_type == ScopeType.URL:
            return target_lower.startswith(value_lower)

        if entry.scope_type == ScopeType.WILDCARD_DOMAIN:
            pattern = value_lower.lstrip("*.")
            return target_lower == pattern or target_lower.endswith(f".{pattern}")

        return False


class AuthorizationManager:
    def __init__(self) -> None:
        self._scope = TargetScope()
        self._investigation_scopes: dict[str, TargetScope] = {}

    @property
    def current_scope(self) -> TargetScope:
        return self._scope

    def set_scope(self, scope: TargetScope) -> None:
        self._scope = scope
        logger.info("Authorization scope updated")

    def create_investigation_scope(self, investigation_id: str) -> TargetScope:
        scope = TargetScope()
        self._investigation_scopes[investigation_id] = scope
        return scope

    def get_investigation_scope(self, investigation_id: str) -> TargetScope | None:
        return self._investigation_scopes.get(investigation_id)

    def check_authorization(self, target: str, investigation_id: str | None = None) -> tuple[bool, str]:
        if investigation_id and investigation_id in self._investigation_scopes:
            scope = self._investigation_scopes[investigation_id]
            if scope.is_target_authorized(target):
                return True, "Target authorized under investigation scope"

        if self._scope.is_target_authorized(target):
            return True, "Target authorized under global scope"

        if self._is_localhost(target):
            return True, "Localhost target always authorized"

        return False, f"Target '{target}' is not within any authorized scope"

    def _is_localhost(self, target: str) -> bool:
        localhost_values = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
        return target.lower().strip() in localhost_values

    def export_scope(self) -> dict[str, Any]:
        return self._scope.model_dump(mode="json")

    def import_scope(self, data: dict[str, Any]) -> None:
        self._scope = TargetScope.model_validate(data)
        logger.info("Scope imported with %d entries", len(self._scope.entries))
