from __future__ import annotations

from typing import Protocol

from .models.finance_budget_facts import FinancePageFacts
from .models.finance_forecast_facts import (
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
