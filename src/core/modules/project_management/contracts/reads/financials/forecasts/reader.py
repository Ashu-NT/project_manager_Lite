from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.reads.financials.budgets.models.budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.forecasts.models.forecast_facts import (
    ForecastLineFact,
    ForecastLineRequest,
    ForecastVersionFact,
    ForecastVersionPageFacts,
    ForecastVersionRequest,
)


class FinanceForecastReader(Protocol):
    def list_versions(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: ForecastVersionRequest,
    ) -> ForecastVersionPageFacts: ...

    def get_version(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        forecast_id: str,
    ) -> ForecastVersionFact | None: ...

    def list_lines(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        forecast_id: str,
        request: ForecastLineRequest,
    ) -> FinancePageFacts[ForecastLineFact]: ...


__all__ = ["FinanceForecastReader"]
