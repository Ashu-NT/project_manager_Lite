from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.audit.domain import AuditEntry, AuditLogEntry


class AuditLogRepository(ABC):
    @abstractmethod
    def add(self, entry: AuditLogEntry) -> None: ...

    @abstractmethod
    def list_recent(
        self,
        limit: int = 200,
        *,
        project_id: str | None = None,
        entity_type: str | None = None,
    ) -> list[AuditLogEntry]: ...

    @abstractmethod
    def list_recent_for_organization(
        self,
        organization_id: str,
        limit: int = 200,
        *,
        project_id: str | None = None,
        entity_type: str | None = None,
    ) -> list[AuditLogEntry]: ...


class AuditRepository(ABC):
    @abstractmethod
    def add(self, entry: AuditEntry) -> None: ...

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


__all__ = ["AuditLogRepository", "AuditRepository"]
