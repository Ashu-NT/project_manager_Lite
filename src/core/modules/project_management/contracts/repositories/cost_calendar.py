from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.modules.project_management.domain.calendar import CalendarEvent, Holiday, WorkingCalendar
from core.modules.project_management.domain.cost import CostItem


class CostRepository(ABC):
    @abstractmethod
    def add(self, cost_item: CostItem) -> None: ...

    @abstractmethod
    def update(self, cost_item: CostItem) -> None: ...

    @abstractmethod
    def delete(self, cost_id: str) -> None: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> List[CostItem]: ...

    @abstractmethod
    def delete_by_project(self, project_id: str) -> None: ...

    @abstractmethod
    def get(self, cost_id: str) -> Optional[CostItem]: ...


class CalendarEventRepository(ABC):
    @abstractmethod
    def add(self, event: CalendarEvent) -> None: ...

    @abstractmethod
    def update(self, event: CalendarEvent) -> None: ...

    @abstractmethod
    def delete(self, event_id: str) -> None: ...

    @abstractmethod
    def get(self, event_id: str) -> Optional[CalendarEvent]: ...

    @abstractmethod
    def list_for_project(self, project_id: str) -> List[CalendarEvent]: ...

    @abstractmethod
    def list_range(self, start_date, end_date) -> List[CalendarEvent]: ...

    @abstractmethod
    def delete_for_task(self, task_id: str) -> None: ...

    @abstractmethod
    def delete_for_project(self, project_id: str) -> None: ...


class WorkingCalendarRepository(ABC):
    @abstractmethod
    def get(self, calendar_id: str) -> Optional[WorkingCalendar]: ...

    @abstractmethod
    def get_default(self) -> Optional[WorkingCalendar]: ...

    @abstractmethod
    def upsert(self, calendar: WorkingCalendar) -> None: ...

    @abstractmethod
    def list_holidays(self, calendar_id: str) -> List[Holiday]: ...

    @abstractmethod
    def add_holiday(self, holiday: Holiday) -> None: ...

    @abstractmethod
    def delete_holiday(self, holiday_id: str) -> None: ...
