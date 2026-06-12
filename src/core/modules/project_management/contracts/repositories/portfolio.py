from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioProjectDependency,
    PortfolioScoringTemplate,
    PortfolioScenario,
)


class PortfolioIntakeRepository(ABC):
    @abstractmethod
    def add(self, item: PortfolioIntakeItem) -> None: ...

    @abstractmethod
    def update(self, item: PortfolioIntakeItem) -> None: ...

    @abstractmethod
    def get(self, item_id: str) -> PortfolioIntakeItem | None: ...

    @abstractmethod
    def get_for_organization(self, item_id: str, organization_id: str) -> PortfolioIntakeItem | None: ...

    @abstractmethod
    def list_for_organization(self, organization_id: str) -> list[PortfolioIntakeItem]: ...

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
    def get_for_organization(self, scenario_id: str, organization_id: str) -> PortfolioScenario | None: ...

    @abstractmethod
    def list_for_organization(self, organization_id: str) -> list[PortfolioScenario]: ...

    @abstractmethod
    def delete(self, scenario_id: str) -> None: ...


class PortfolioProjectDependencyRepository(ABC):
    @abstractmethod
    def add(self, dependency: PortfolioProjectDependency) -> None: ...

    @abstractmethod
    def get_for_organization(
        self,
        dependency_id: str,
        organization_id: str,
    ) -> PortfolioProjectDependency | None: ...

    @abstractmethod
    def list_for_organization(self, organization_id: str) -> list[PortfolioProjectDependency]: ...

    @abstractmethod
    def delete_for_organization(self, dependency_id: str, organization_id: str) -> None: ...


class PortfolioScoringTemplateRepository(ABC):
    @abstractmethod
    def add(self, template: PortfolioScoringTemplate) -> None: ...

    @abstractmethod
    def update(self, template: PortfolioScoringTemplate) -> None: ...

    @abstractmethod
    def get(self, template_id: str) -> PortfolioScoringTemplate | None: ...

    @abstractmethod
    def get_for_organization(self, template_id: str, organization_id: str) -> PortfolioScoringTemplate | None: ...

    @abstractmethod
    def list_for_organization(self, organization_id: str) -> list[PortfolioScoringTemplate]: ...
