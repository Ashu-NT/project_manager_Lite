from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FinancialLedgerRowDto:
    source_label: str
    stage: str
    amount: float
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
    planned: float
    planned_label: str
    committed: float
    committed_label: str
    actual: float
    actual_label: str
    forecast: float
    forecast_label: str
    exposure: float
    exposure_label: str


@dataclass(frozen=True)
class FinancialAnalyticsRowDto:
    dimension: str
    key: str
    label: str
    planned: float
    planned_label: str
    committed: float
    committed_label: str
    actual: float
    actual_label: str
    forecast: float
    forecast_label: str
    exposure: float
    exposure_label: str


@dataclass(frozen=True)
class FinancialSnapshotDto:
    project_id: str
    project_currency: str | None
    budget: float
    budget_label: str
    planned: float
    planned_label: str
    committed: float
    committed_label: str
    actual: float
    actual_label: str
    exposure: float
    exposure_label: str
    available: float | None
    available_label: str
    ledger: tuple[FinancialLedgerRowDto, ...]
    cashflow: tuple[FinancialPeriodRowDto, ...]
    by_source: tuple[FinancialAnalyticsRowDto, ...]
    by_cost_type: tuple[FinancialAnalyticsRowDto, ...]
    by_resource: tuple[FinancialAnalyticsRowDto, ...]
    by_task: tuple[FinancialAnalyticsRowDto, ...]
    notes: tuple[str, ...]


__all__ = [
    "FinancialAnalyticsRowDto",
    "FinancialLedgerRowDto",
    "FinancialPeriodRowDto",
    "FinancialSnapshotDto",
]
