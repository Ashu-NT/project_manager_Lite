from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.platform.approval.domain import ApprovalRequest, ApprovalStatus
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


class ApprovalRepository(ABC):
    @abstractmethod
    def add(self, request: ApprovalRequest) -> None: ...

    @abstractmethod
    def update(self, request: ApprovalRequest) -> None: ...

    @abstractmethod
    def get(self, request_id: str) -> Optional[ApprovalRequest]: ...

    @abstractmethod
    def list_by_status(
        self,
        status: ApprovalStatus | None = None,
        *,
        limit: int = 200,
        project_id: str | None = None,
        entity_type: str | list[str] | None = None,
        entity_id: str | None = None,
    ) -> List[ApprovalRequest]: ...


__all__ = [
    "ApprovalRepository",
    "AuditLogRepository",
    "TimeEntryRepository",
    "TimesheetPeriodRepository",
]
