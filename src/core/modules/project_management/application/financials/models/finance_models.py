from __future__ import annotations

from dataclasses import dataclass
from datetime import date

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
    unresolved_labor_rates: tuple[UnresolvedLaborRate, ...] = ()


# ── Cost DTOs ─────────────────────────────────────────────────────────────────

@dataclass
class CostSourceRow:
    source_key: str
    source_label: str
    planned: float
    committed: float
    actual: float


@dataclass
class CostSourceBreakdown:
    project_id: str
    project_currency: str | None
    rows: list[CostSourceRow]
    total_planned: float
    total_committed: float
    total_actual: float
    notes: list[str]


@dataclass
class CostBreakdownRow:
    cost_type: str
    currency: str
    planned: float
    actual: float


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


@dataclass
class LaborPlanActualRow:
    resource_id: str
    resource_name: str
    planned_hours: float
    planned_hourly_rate: float
    planned_currency_code: str | None
    planned_cost: float
    actual_hours: float
    actual_currency_code: str | None
    actual_cost: float
    variance_cost: float


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

    @property
    def is_complete(self) -> bool:
        return not self.unresolved_rates


@dataclass(frozen=True)
class LaborPlanResult:
    rows: tuple[LaborPlanActualRow, ...]
    unresolved_rates: tuple[UnresolvedLaborRate, ...]

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
    "FinanceSnapshot",
    # Cost
    "CostSourceRow",
    "CostSourceBreakdown",
    "CostBreakdownRow",
    # Labor
    "LaborAssignmentRow",
    "LaborResourceRow",
    "LaborPlanActualRow",
    "LaborDetailsResult",
    "LaborPlanResult",
    # EVM
    "EarnedValueMetrics",
    "EvmSeriesPoint",
]
