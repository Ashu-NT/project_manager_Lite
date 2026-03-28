from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Protocol

from core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus


class WorkAssignmentRecord(Protocol):
    id: str
    task_id: str
    resource_id: str
    hours_logged: float


class WorkTaskRecord(Protocol):
    id: str
    project_id: str
    name: str
    start_date: date | None
    actual_start: date | None


class WorkResourceRecord(Protocol):
    id: str
    name: str
    employee_id: str | None


class WorkAssignmentRepository(Protocol):
    def get(self, assignment_id: str) -> WorkAssignmentRecord | None: ...

    def list_by_resource(self, resource_id: str) -> list[WorkAssignmentRecord]: ...

    def update(self, assignment: WorkAssignmentRecord) -> None: ...


class WorkTaskRepository(Protocol):
    def get(self, task_id: str) -> WorkTaskRecord | None: ...


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
    def list_by_assignment(self, assignment_id: str) -> list[TimeEntry]: ...

    @abstractmethod
    def delete_by_assignment(self, assignment_id: str) -> None: ...


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


__all__ = [
    "TimeEntryRepository",
    "TimesheetPeriodRepository",
    "WorkAssignmentRecord",
    "WorkAssignmentRepository",
    "WorkResourceRecord",
    "WorkResourceRepository",
    "WorkTaskRecord",
    "WorkTaskRepository",
]
