from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Protocol

from src.core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus


class WorkAllocationRecord(Protocol):
    id: str
    resource_id: str
    hours_logged: float


class WorkOwnerRecord(Protocol):
    id: str
    name: str


class WorkResourceRecord(Protocol):
    id: str
    name: str
    employee_id: str | None


class WorkAllocationRepository(Protocol):
    def get(self, work_allocation_id: str) -> WorkAllocationRecord | None: ...

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
    def list_all(
        self,
        *,
        status: TimesheetPeriodStatus | None = None,
        limit: int | None = None,
    ) -> list[TimesheetPeriod]: ...


WorkAssignmentRecord = WorkAllocationRecord
WorkAssignmentRepository = WorkAllocationRepository
WorkTaskRecord = WorkOwnerRecord
WorkTaskRepository = WorkOwnerRepository


__all__ = [
    "TimeEntryRepository",
    "TimesheetPeriodRepository",
    "WorkAllocationRecord",
    "WorkAllocationRepository",
    "WorkAssignmentRecord",
    "WorkAssignmentRepository",
    "WorkOwnerRecord",
    "WorkOwnerRepository",
    "WorkResourceRecord",
    "WorkResourceRepository",
    "WorkTaskRecord",
    "WorkTaskRepository",
]
