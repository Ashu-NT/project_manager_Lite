from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Protocol

from src.core.platform.contract.interface.time_management.time.contracts import (
    WorkAllocationRecord,
    WorkOwnerRecord,
    WorkResourceRecord,
)
from src.core.platform.domain.time_management.time import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus


class WorkAllocationRepository(Protocol):
    def get(self, work_allocation_id: str) -> WorkAllocationRecord | None: ...

    def list_by_ids(self, work_allocation_ids: list[str]) -> list[WorkAllocationRecord]: ...

    def list_by_resource(self, resource_id: str) -> list[WorkAllocationRecord]: ...

    def update(self, work_allocation: WorkAllocationRecord) -> None: ...


class WorkOwnerRepository(Protocol):
    def get(self, owner_id: str) -> WorkOwnerRecord | None: ...


class WorkResourceRepository(Protocol):
    def get(self, resource_id: str) -> WorkResourceRecord | None: ...


class TimeEntryRepository(ABC):
    @abstractmethod
    def add(self, entry: TimeEntry) -> None: ...

    @abstractmethod
    def get(self, entry_id: str) -> TimeEntry | None: ...

    @abstractmethod
    def update(self, entry: TimeEntry) -> None: ...

    @abstractmethod
    def delete(self, entry_id: str) -> None: ...

    @abstractmethod
    def list_by_work_allocation(self, work_allocation_id: str) -> list[TimeEntry]: ...

    @abstractmethod
    def delete_by_work_allocation(self, work_allocation_id: str) -> None: ...

    def list_by_work_allocations(self, work_allocation_ids: list[str]) -> list[TimeEntry]:
        """Batched multi-assignment lookup -- default falls back to one call
        per id; concrete repositories should override with a real IN(...)
        query. Used by task-scoped time views that span every TaskAssignment
        on a task, never just one (docs §44 Time redesign)."""
        entries: list[TimeEntry] = []
        for work_allocation_id in work_allocation_ids:
            entries.extend(self.list_by_work_allocation(work_allocation_id))
        return entries

    def list_by_assignment(self, assignment_id: str) -> list[TimeEntry]:
        return self.list_by_work_allocation(assignment_id)

    def delete_by_assignment(self, assignment_id: str) -> None:
        self.delete_by_work_allocation(assignment_id)


class TimesheetPeriodRepository(ABC):
    @abstractmethod
    def add(self, period: TimesheetPeriod) -> None: ...

    @abstractmethod
    def get(self, period_id: str) -> TimesheetPeriod | None: ...

    @abstractmethod
    def update(self, period: TimesheetPeriod) -> None: ...

    @abstractmethod
    def get_by_resource_period(self, resource_id: str, period_start: date) -> TimesheetPeriod | None: ...

    @abstractmethod
    def list_by_resource(self, resource_id: str) -> list[TimesheetPeriod]: ...

    @abstractmethod
    def list_review_candidates(
        self,
        *,
        organization_id: str | None = None,
        status: TimesheetPeriodStatus | None = None,
        limit: int | None = None,
    ) -> list[TimesheetPeriod]: ...


WorkAssignmentRepository = WorkAllocationRepository
WorkTaskRepository = WorkOwnerRepository


__all__ = [
    "TimeEntryRepository",
    "TimesheetPeriodRepository",
    "WorkAllocationRepository",
    "WorkAssignmentRepository",
    "WorkOwnerRepository",
    "WorkResourceRepository",
    "WorkTaskRepository",
]
