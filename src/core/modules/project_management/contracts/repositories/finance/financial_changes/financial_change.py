from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeRequest,
)


class FinancialChangeRepository(ABC):
    @abstractmethod
    def add(self, change: FinancialChangeRequest) -> None: ...

    @abstractmethod
    def get(self, change_id: str) -> FinancialChangeRequest | None: ...

    @abstractmethod
    def get_latest_for_project(self, project_id: str) -> FinancialChangeRequest | None: ...

    @abstractmethod
    def list_for_project(self, project_id: str) -> list[FinancialChangeRequest]: ...

    @abstractmethod
    def update(self, change: FinancialChangeRequest, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def get_impact(self, impact_id: str) -> FinancialChangeImpact | None: ...

    @abstractmethod
    def add_impact(self, impact: FinancialChangeImpact) -> None: ...

    @abstractmethod
    def update_impact(
        self, impact: FinancialChangeImpact, *, expected_row_version: int
    ) -> None: ...

    @abstractmethod
    def delete_impact(self, impact_id: str, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def list_impacts(self, change_id: str) -> list[FinancialChangeImpact]: ...

    @abstractmethod
    def update_impact_application(
        self,
        impact_id: str,
        *,
        applied_reference_type: str,
        applied_reference_id: str,
    ) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...


__all__ = ["FinancialChangeRepository"]
