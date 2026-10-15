from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.application.financials.cost.dto import (
    ProjectFinanceLedgerRow,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    CostPhasingSeriesAvailabilityFact,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    UnresolvedLaborRate,
)


@dataclass(frozen=True)
class FinancePeriodRow:
    period_key: str
    period_start: date
    period_end: date
    planned: Decimal
    committed: Decimal
    actual: Decimal
    forecast: Decimal
    exposure: Decimal


@dataclass(frozen=True)
class FinanceAnalyticsRow:
    dimension: str
    key: str
    label: str
    planned: Decimal
    committed: Decimal
    actual: Decimal
    forecast: Decimal
    exposure: Decimal


@dataclass(frozen=True)
class FinanceReconciliation:
    posted_actual_control: Decimal
    posted_actual_ledger: Decimal
    open_commitment_control: Decimal
    open_commitment_ledger: Decimal
    forecast_etc_control: Decimal | None
    forecast_etc_ledger: Decimal | None

    @property
    def posted_actual_delta(self) -> Decimal:
        return self.posted_actual_ledger - self.posted_actual_control

    @property
    def open_commitment_delta(self) -> Decimal:
        return self.open_commitment_ledger - self.open_commitment_control

    @property
    def forecast_etc_delta(self) -> Decimal | None:
        if self.forecast_etc_control is None or self.forecast_etc_ledger is None:
            return None
        return self.forecast_etc_ledger - self.forecast_etc_control

    @property
    def is_reconciled(self) -> bool:
        return (
            self.posted_actual_delta == 0
            and self.open_commitment_delta == 0
            and (
                (self.forecast_etc_control is None and self.forecast_etc_ledger is None)
                or self.forecast_etc_delta == 0
            )
        )


@dataclass(frozen=True)
class FinanceSnapshot:
    project_id: str
    project_currency: str | None
    budget: Decimal
    planned: Decimal
    committed: Decimal
    actual: Decimal
    forecast_etc: Decimal | None
    estimate_at_completion: Decimal | None
    budget_headroom: Decimal | None
    exposure: Decimal
    available: Decimal | None
    as_of: date
    approved_budget_id: str | None
    approved_budget_revision: int | None
    approved_forecast_id: str | None
    approved_forecast_revision: int | None
    approved_forecast_as_of: date | None
    currency_basis: str
    period_granularity: str
    sensitive_detail_included: bool
    reconciliation: FinanceReconciliation
    ledger: list[ProjectFinanceLedgerRow]
    cost_phasing: list[FinancePeriodRow]
    cost_phasing_availability: tuple[CostPhasingSeriesAvailabilityFact, ...]
    by_source: list[FinanceAnalyticsRow]
    ledger_total: int
    ledger_offset: int
    ledger_limit: int
    notes: list[str]
    unresolved_labor_rates: tuple[UnresolvedLaborRate, ...] = ()


__all__ = ['FinancePeriodRow', 'FinanceAnalyticsRow', 'FinanceReconciliation', 'FinanceSnapshot']
