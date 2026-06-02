from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.calendar.domain import Holiday, WorkingCalendar


class WorkingCalendarRepository(ABC):
    @abstractmethod
    def get(self, calendar_id: str) -> WorkingCalendar | None: ...

    @abstractmethod
    def get_default(self) -> WorkingCalendar | None: ...

    @abstractmethod
    def upsert(self, calendar: WorkingCalendar) -> None: ...

    @abstractmethod
    def list_holidays(self, calendar_id: str) -> list[Holiday]: ...

    @abstractmethod
    def add_holiday(self, holiday: Holiday) -> None: ...

    @abstractmethod
    def delete_holiday(self, holiday_id: str) -> None: ...


__all__ = ["WorkingCalendarRepository"]
