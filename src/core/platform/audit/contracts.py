from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.audit.domain import AuditEntry


class AuditRepository(ABC):
    @abstractmethod
    def add(self, entry: AuditEntry) -> None: ...

    @abstractmethod
    def add_for_tenant(self, entry: AuditEntry, tenant_id: str) -> None:
        """Persist an explicitly scoped security event without organization context."""
        ...

    @abstractmethod
    def add_platform(self, entry: AuditEntry) -> None:
        """Persist an explicitly platform-scoped security event."""
        ...

    @abstractmethod
    def list_recent(
        self,
        limit: int = 100,
        *,
        entity_type: str | None = None,
        operation: str | None = None,
        severity: str | None = None,
        compliance_tag: str | None = None,
    ) -> list[AuditEntry]: ...

    @abstractmethod
    def list_recent_for_organization(
        self,
        organization_id: str,
        limit: int = 100,
        *,
        entity_type: str | None = None,
        operation: str | None = None,
        severity: str | None = None,
    ) -> list[AuditEntry]: ...


__all__ = ["AuditRepository"]
