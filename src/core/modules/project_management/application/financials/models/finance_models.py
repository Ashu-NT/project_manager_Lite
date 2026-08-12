from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.contracts.repositories.rate_resolution import (
    UnresolvedLaborRate,
)


# ── Finance snapshot DTOs ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class FinanceLedgerRow:
    project_id: str
    source_key: str
    source_label: str
    cost_type: str
    stage: str
    amount: Decimal
    currency: str | None
    occurred_on: date | None
    reference_type: str
    reference_id: str
    reference_label: str
    task_id: str | None
    task_name: str | None
    resource_id: str | None
    resource_name: str | None
    cost_code_id: str | None
    source_type: str | None
    financial_period_id: str | None
    period_start: date | None
    period_end: date | None
    included_in_policy: bool


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
                (
                    self.forecast_etc_control is None
                    and self.forecast_etc_ledger is None
                )
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
    variance_at_completion: Decimal | None
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
    ledger: list[FinanceLedgerRow]
    cashflow: list[FinancePeriodRow]
    by_source: list[FinanceAnalyticsRow]
    by_cost_type: list[FinanceAnalyticsRow]
    by_resource: list[FinanceAnalyticsRow]
    by_task: list[FinanceAnalyticsRow]
    notes: list[str]
    unresolved_labor_rates: tuple[UnresolvedLaborRate, ...] = ()

    @property
    def commitment_rate_percent(self) -> Decimal:
        if self.budget <= 0:
            return Decimal("0")
        return (self.committed / self.budget) * Decimal("100")


# ── Cost DTOs ─────────────────────────────────────────────────────────────────

@dataclass
class CostSourceRow:
    source_key: str
    source_label: str
    planned: Decimal
    committed: Decimal
    actual: Decimal
    forecast: Decimal


@dataclass
class CostSourceBreakdown:
    project_id: str
    project_currency: str | None
    rows: list[CostSourceRow]
    total_planned: Decimal
    total_committed: Decimal
    total_actual: Decimal
    notes: list[str]


@dataclass
class CostBreakdownRow:
    cost_type: str
    currency: str
    planned: Decimal
    actual: Decimal


# ── Commercial / profitability DTOs (ADR-PF-010) ───────────────────────────────

@dataclass(frozen=True)
class ProjectCommercialProjection:
    """ADR-PF-010's five commercial projections. contract_value/billable_amount/
    externally_invoiced_amount/externally_paid_amount are ordinary Project
    Finance authority data (finance.read); forecast_revenue_at_completion/
    revenue_basis/projected_margin_* are further redacted without
    finance.read_profitability (profitability_detail_included is False, all
    four are None/"") -- the same mixed-content pattern as
    ProjectKPI.financial_detail_included."""

    project_id: str
    project_currency: str | None
    contract_value: Decimal | None
    billable_amount: Decimal
    externally_invoiced_amount: Decimal
    externally_paid_amount: Decimal
    external_accounting_data_available: bool
    forecast_revenue_at_completion: Decimal | None
    revenue_basis: str
    projected_margin_amount: Decimal | None
    projected_margin_percent: Decimal | None
    profitability_detail_included: bool = True


# ── Labor DTOs ────────────────────────────────────────────────────────────────

@dataclass
class LaborAssignmentRow:
    assignment_id: str
    task_id: str
    task_name: str
    hours: float
    hourly_rate: float
    currency_code: str | None
    cost: float


@dataclass
class LaborResourceRow:
    resource_id: str
    resource_name: str
    total_hours: float
    hourly_rate: float
    currency_code: str | None
    total_cost: float
    assignments: list[LaborAssignmentRow]


@dataclass(frozen=True)
class PlannedLaborResourceRow:
    project_resource_id: str
    resource_id: str
    resource_name: str
    planned_hours: float
    hourly_rate: float
    currency_code: str | None
    total_cost: float


@dataclass(frozen=True)
class LaborDetailsResult:
    """Rich result for labor details — rows plus which resources' rates
    could not be resolved, so a caller can tell "no labor cost" apart from
    "some labor cost we couldn't price." The existing list-returning
    ``get_project_labor_details`` is a thin wrapper over this — one
    computation, not a second query to separately answer what was
    unresolved."""

    rows: tuple[LaborResourceRow, ...]
    unresolved_rates: tuple[UnresolvedLaborRate, ...]
    planned_rows: tuple[PlannedLaborResourceRow, ...] = ()
    planned_unresolved_rates: tuple[UnresolvedLaborRate, ...] = ()

    @property
    def is_complete(self) -> bool:
        return not self.unresolved_rates


# ── Earned Value DTOs ─────────────────────────────────────────────────────────

@dataclass
class EvmSeriesPoint:
    period_end: date
    PV: float
    EV: float
    AC: float
    BAC: float
    CPI: float
    SPI: float


@dataclass
class EarnedValueMetrics:
    as_of: date
    baseline_id: str

    BAC: float
    PV: float
    EV: float
    AC: float

    CPI: float | None
    SPI: float | None
    EAC: float | None
    ETC: float | None
    VAC: float | None
    TCPI_to_BAC: float | None = None
    TCPI_to_EAC: float | None = None
    notes: str | None = None


__all__ = [
    # Finance snapshot
    "FinanceLedgerRow",
    "FinancePeriodRow",
    "FinanceAnalyticsRow",
    "FinanceReconciliation",
    "FinanceSnapshot",
    # Cost
    "CostSourceRow",
    "CostSourceBreakdown",
    "CostBreakdownRow",
    # Commercial / profitability
    "ProjectCommercialProjection",
    # Labor
    "LaborAssignmentRow",
    "LaborResourceRow",
    "PlannedLaborResourceRow",
    "LaborDetailsResult",
    # EVM
    "EarnedValueMetrics",
    "EvmSeriesPoint",
]
