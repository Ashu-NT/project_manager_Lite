from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

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
    def get(self, item_id: str) -> Optional[PortfolioIntakeItem]: ...

    @abstractmethod
    def get_for_organization(self, item_id: str, organization_id: str) -> Optional[PortfolioIntakeItem]: ...

    @abstractmethod
    def list_for_organization(self, organization_id: str) -> List[PortfolioIntakeItem]: ...

    @abstractmethod
    def delete(self, item_id: str) -> None: ...


class PortfolioScenarioRepository(ABC):
    @abstractmethod
    def add(self, scenario: PortfolioScenario) -> None: ...

    @abstractmethod
    def update(self, scenario: PortfolioScenario) -> None: ...

    @abstractmethod
    def get(self, scenario_id: str) -> Optional[PortfolioScenario]: ...

    @abstractmethod
    def get_for_organization(self, scenario_id: str, organization_id: str) -> Optional[PortfolioScenario]: ...

    @abstractmethod
    def list_for_organization(self, organization_id: str) -> List[PortfolioScenario]: ...

    @abstractmethod
    def delete(self, scenario_id: str) -> None: ...


class PortfolioProjectDependencyRepository(ABC):
    @abstractmethod
    def add(self, dependency: PortfolioProjectDependency) -> None: ...

    @abstractmethod
    def get(self, dependency_id: str) -> Optional[PortfolioProjectDependency]: ...

    @abstractmethod
    def list_for_organization(self, organization_id: str) -> List[PortfolioProjectDependency]: ...

    @abstractmethod
    def delete(self, dependency_id: str) -> None: ...


class PortfolioScoringTemplateRepository(ABC):
    @abstractmethod
    def add(self, template: PortfolioScoringTemplate) -> None: ...

    @abstractmethod
    def update(self, template: PortfolioScoringTemplate) -> None: ...

    @abstractmethod
    def get(self, template_id: str) -> Optional[PortfolioScoringTemplate]: ...

    @abstractmethod
    def get_for_organization(self, template_id: str, organization_id: str) -> Optional[PortfolioScoringTemplate]: ...

    @abstractmethod
    def list_for_organization(self, organization_id: str) -> List[PortfolioScoringTemplate]: ...
