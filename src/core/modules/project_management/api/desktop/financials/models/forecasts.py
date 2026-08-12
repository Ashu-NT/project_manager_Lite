from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FinancialForecastDto:
    project_id: str
    basis: str
    basis_label: str
    budget: str
    budget_label: str
    actual: str
    actual_label: str
    etc: str | None
    etc_label: str
    eac: str | None
    eac_label: str
    vac: str | None
    vac_label: str
    is_over_budget: bool
    has_approved_forecast: bool
    forecast_revision: int | None
    forecast_as_of: date | None


__all__ = ["FinancialForecastDto"]
