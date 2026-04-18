from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.audit.domain import AuditLogEntry


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


__all__ = ["AuditLogRepository"]
