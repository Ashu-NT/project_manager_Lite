from __future__ import annotations

from abc import ABC, abstractmethod

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
