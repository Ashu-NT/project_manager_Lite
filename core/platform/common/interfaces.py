from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.platform.audit.domain import AuditLogEntry
from src.core.platform.time.contracts import TimeEntryRepository, TimesheetPeriodRepository


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
    ) -> List[AuditLogEntry]: ...


__all__ = [
    "AuditLogRepository",
    "TimeEntryRepository",
    "TimesheetPeriodRepository",
]
