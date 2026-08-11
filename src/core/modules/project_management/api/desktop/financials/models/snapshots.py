from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FinancialLedgerRowDto:
    source_label: str
    stage: str
    amount: str
    amount_label: str
    reference_label: str
    task_name: str
    resource_name: str
    occurred_on: date | None
    occurred_on_label: str
    included_in_policy: bool


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


@dataclass(frozen=True)
class FinancialAnalyticsRowDto:
    dimension: str
    key: str
    label: str
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


@dataclass(frozen=True)
class FinancialSnapshotDto:
    project_id: str
    project_currency: str | None
    budget: str
    budget_label: str
    planned: str
    planned_label: str
    committed: str
    committed_label: str
    actual: str
    actual_label: str
    exposure: str
    exposure_label: str
    available: str | None
    available_label: str
    ledger: tuple[FinancialLedgerRowDto, ...]
    cashflow: tuple[FinancialPeriodRowDto, ...]
    by_source: tuple[FinancialAnalyticsRowDto, ...]
    by_cost_type: tuple[FinancialAnalyticsRowDto, ...]
    by_resource: tuple[FinancialAnalyticsRowDto, ...]
    by_task: tuple[FinancialAnalyticsRowDto, ...]
    notes: tuple[str, ...]
    labor_rates_complete: bool = True
    unresolved_labor_rate_count: int = 0
    forecast_etc: str | None = None
    forecast_etc_label: str = "Not approved"
    estimate_at_completion: str | None = None
    estimate_at_completion_label: str = "Not available"
    variance_at_completion: str | None = None
    variance_at_completion_label: str = "Not available"
    as_of: date | None = None
    approved_budget_id: str = ""
    approved_budget_revision: int | None = None
    approved_forecast_id: str = ""
    approved_forecast_revision: int | None = None
    approved_forecast_as_of: date | None = None


__all__ = [
    "FinancialAnalyticsRowDto",
    "FinancialLedgerRowDto",
    "FinancialPeriodRowDto",
    "FinancialSnapshotDto",
]
