from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from datetime import datetime


@dataclass(frozen=True)
class FinancialOverviewDto:
    project_id: str
    project_currency: str | None
    as_of: date | None
    budget: str
    budget_label: str
    actual: str
    actual_label: str
    committed: str
    committed_label: str
    available: str
    available_label: str
    forecast_etc: str | None
    forecast_etc_label: str
    estimate_at_completion: str | None
    estimate_at_completion_label: str
    variance_at_completion: str | None
    variance_at_completion_label: str
    approved_budget_id: str = ""
    approved_budget_revision: int | None = None
    approved_budget_at: datetime | None = None
    approved_forecast_id: str = ""
    approved_forecast_revision: int | None = None
    approved_forecast_as_of: date | None = None


@dataclass(frozen=True)
class FinancialPeriodRowDto:
    period_key: str
    planned: str
    planned_label: str
    committed: str
    committed_label: str
    actual: str
    actual_label: str
    forecast: str
    forecast_label: str
    exposure: str
    exposure_label: str


__all__ = [
    "FinancialPeriodRowDto",
    "FinancialOverviewDto",
]
