from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from core.platform.time.domain import TimeEntry, TimesheetPeriod


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


__all__ = ["TimeEntryRepository", "TimesheetPeriodRepository"]
