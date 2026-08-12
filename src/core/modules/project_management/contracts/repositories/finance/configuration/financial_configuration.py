from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.financials.configuration import (
    ProjectCostCode,
    ProjectCostCodeRestriction,
    ProjectFinancialProfile,
)


class ProjectFinancialProfileRepository(ABC):
    @abstractmethod
    def add(self, profile: ProjectFinancialProfile) -> None: ...

    @abstractmethod
    def get_by_project(self, project_id: str) -> ProjectFinancialProfile | None: ...

    @abstractmethod
    def update(self, profile: ProjectFinancialProfile) -> None: ...


class ProjectCostCodeRepository(ABC):
    @abstractmethod
    def add(self, cost_code: ProjectCostCode) -> None: ...

    @abstractmethod
    def get(self, cost_code_id: str) -> ProjectCostCode | None: ...

    @abstractmethod
    def get_by_code(self, code: str) -> ProjectCostCode | None: ...

    @abstractmethod
    def list(self, *, include_inactive: bool = False) -> list[ProjectCostCode]: ...

    @abstractmethod
    def update(self, cost_code: ProjectCostCode) -> None: ...

    @abstractmethod
    def add_restriction(self, restriction: ProjectCostCodeRestriction) -> None: ...

    @abstractmethod
    def remove_restriction(self, *, project_id: str, cost_code_id: str) -> None: ...

    @abstractmethod
    def list_restrictions(self, project_id: str) -> list[ProjectCostCodeRestriction]: ...

    @abstractmethod
    def is_default_for_any_profile(self, cost_code_id: str) -> bool: ...


__all__ = ["ProjectCostCodeRepository", "ProjectFinancialProfileRepository"]
