from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FinanceLedgerRow:
    project_id: str
    source_key: str
    source_label: str
    cost_type: str
    stage: str
    amount: float
    currency: str | None
    occurred_on: date | None
    reference_type: str
    reference_id: str
    reference_label: str
    task_id: str | None
    task_name: str | None
    resource_id: str | None
    resource_name: str | None
    included_in_policy: bool


@dataclass(frozen=True)
class FinancePeriodRow:
    period_key: str
    period_start: date
    period_end: date
    planned: float
    committed: float
    actual: float
    forecast: float
    exposure: float


@dataclass(frozen=True)
class FinanceAnalyticsRow:
    dimension: str
    key: str
    label: str
    planned: float
    committed: float
    actual: float
    forecast: float
    exposure: float


@dataclass(frozen=True)
class FinanceSnapshot:
    project_id: str
    project_currency: str | None
    budget: float
    planned: float
    committed: float
    actual: float
    exposure: float
    available: float | None
    ledger: list[FinanceLedgerRow]
    cashflow: list[FinancePeriodRow]
    by_source: list[FinanceAnalyticsRow]
    by_cost_type: list[FinanceAnalyticsRow]
    by_resource: list[FinanceAnalyticsRow]
    by_task: list[FinanceAnalyticsRow]
    notes: list[str]


__all__ = [
    "FinanceLedgerRow",
    "FinancePeriodRow",
    "FinanceAnalyticsRow",
    "FinanceSnapshot",
]
