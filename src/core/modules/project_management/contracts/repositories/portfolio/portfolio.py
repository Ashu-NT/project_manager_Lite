from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.core.modules.project_management.application.common.pagination import PaginatedResult
from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioProjectDependency,
    PortfolioScoringTemplate,
    PortfolioScenario,
)


@dataclass(frozen=True, slots=True)
class PortfolioProjectDependencyPageItem:
    """A paginated dependency row plus the joined predecessor/successor
    project labels the query layer already has on hand from its SQL join —
    avoids a second, unbounded project lookup just to label a page."""

    dependency: PortfolioProjectDependency
    predecessor_project_name: str
    predecessor_project_status: str
    successor_project_name: str
    successor_project_status: str


class PortfolioIntakeRepository(ABC):
    @abstractmethod
    def add(self, item: PortfolioIntakeItem) -> None: ...

    @abstractmethod
    def update(self, item: PortfolioIntakeItem) -> None: ...

    @abstractmethod
    def get(self, item_id: str) -> PortfolioIntakeItem | None: ...

    @abstractmethod
    def list(self) -> list[PortfolioIntakeItem]: ...

    @abstractmethod
    def list_page(
        self,
        *,
        status: PortfolioIntakeStatus | None,
        search_text: str,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> PaginatedResult[PortfolioIntakeItem]: ...

    @abstractmethod
    def delete(self, item_id: str) -> None: ...


class PortfolioScenarioRepository(ABC):
    @abstractmethod
    def add(self, scenario: PortfolioScenario) -> None: ...

    @abstractmethod
    def update(self, scenario: PortfolioScenario) -> None: ...

    @abstractmethod
    def get(self, scenario_id: str) -> PortfolioScenario | None: ...

    @abstractmethod
    def list(self) -> list[PortfolioScenario]: ...

    @abstractmethod
    def delete(self, scenario_id: str) -> None: ...


class PortfolioProjectDependencyRepository(ABC):
    @abstractmethod
    def add(self, dependency: PortfolioProjectDependency) -> None: ...

    @abstractmethod
    def get(self, dependency_id: str) -> PortfolioProjectDependency | None: ...

    @abstractmethod
    def list(self) -> list[PortfolioProjectDependency]: ...

    @abstractmethod
    def list_page(
        self,
        *,
        search_text: str,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> PaginatedResult[PortfolioProjectDependencyPageItem]: ...

    @abstractmethod
    def delete(self, dependency_id: str) -> None: ...


class PortfolioScoringTemplateRepository(ABC):
    @abstractmethod
    def add(self, template: PortfolioScoringTemplate) -> None: ...

    @abstractmethod
    def update(self, template: PortfolioScoringTemplate) -> None: ...

    @abstractmethod
    def get(self, template_id: str) -> PortfolioScoringTemplate | None: ...

    @abstractmethod
    def list(self) -> list[PortfolioScoringTemplate]: ...
