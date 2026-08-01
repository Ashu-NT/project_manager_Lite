from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.scheduling.calendar import CalendarEvent
from src.core.modules.project_management.domain.financials.cost import CostItem


class CostRepository(ABC):
    @abstractmethod
    def add(self, cost_item: CostItem) -> None: ...

    @abstractmethod
    def update(self, cost_item: CostItem) -> None: ...

    @abstractmethod
    def delete(self, cost_id: str) -> None: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> list[CostItem]: ...

    @abstractmethod
    def delete_by_project(self, project_id: str) -> None: ...

    @abstractmethod
    def get(self, cost_id: str) -> CostItem | None: ...


class CalendarEventRepository(ABC):
    @abstractmethod
    def add(self, event: CalendarEvent) -> None: ...

    @abstractmethod
    def update(self, event: CalendarEvent) -> None: ...

    @abstractmethod
    def delete(self, event_id: str) -> None: ...

    @abstractmethod
    def get(self, event_id: str) -> CalendarEvent | None: ...

    @abstractmethod
    def list_for_project(self, project_id: str) -> list[CalendarEvent]: ...

    @abstractmethod
    def list_range(self, start_date, end_date) -> list[CalendarEvent]: ...

    @abstractmethod
    def delete_for_task(self, task_id: str) -> None: ...

    @abstractmethod
    def delete_for_project(self, project_id: str) -> None: ...
