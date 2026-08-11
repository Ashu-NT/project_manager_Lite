"""Immutable canonical database facts used to compose finance snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FinanceProjectFact:
    project_id: str
    tenant_id: str
    organization_id: str
    currency_code: str
    approved_budget: Decimal
    approved_budget_id: str | None
    approved_budget_revision: int | None
    start_date: date | None
    end_date: date | None


@dataclass(frozen=True, slots=True)
class TaskFact:
    task_id: str
    name: str
    percent_complete: float
    start_date: date | None
    end_date: date | None
    actual_start: date | None
    actual_end: date | None


@dataclass(frozen=True, slots=True)
class FinanceLedgerFact:
    """One planned, committed, or actual row from a canonical authority."""

    fact_id: str
    task_id: str | None
    resource_id: str | None
    description: str
    source_key: str
    source_label: str
    reference_type: str
    cost_type: str
    stage: str
    currency_code: str | None
    amount: Decimal
    occurred_on: date | None
    cost_code_id: str | None = None
    source_type: str | None = None
    financial_period_id: str | None = None
    period_start: date | None = None
    period_end: date | None = None


@dataclass(frozen=True, slots=True)
class CostAggregateFact:
    """Canonical financial totals grouped by stage, type, and currency."""

    stage: str
    cost_type: str
    currency_code: str | None
    total_amount: Decimal
    row_count: int


@dataclass(frozen=True, slots=True)
class ApprovedForecastFact:
    """The one approved ETC version selected for this read basis."""

    forecast_id: str
    revision: int
    name: str
    currency_code: str
    as_of_date: date
    etc_total: Decimal
    line_count: int


@dataclass(frozen=True, slots=True)
class FinanceControlFact:
    """Reconciled project-currency totals from canonical financial authorities."""

    approved_budget: Decimal
    posted_actual: Decimal
    open_commitment: Decimal
    forecast_etc: Decimal | None

    @property
    def estimate_at_completion(self) -> Decimal | None:
        if self.forecast_etc is None:
            return None
        return self.posted_actual + self.forecast_etc

    @property
    def variance_at_completion(self) -> Decimal | None:
        eac = self.estimate_at_completion
        return None if eac is None else self.approved_budget - eac

    @property
    def committed_available(self) -> Decimal:
        return self.approved_budget - self.posted_actual - self.open_commitment


@dataclass(frozen=True, slots=True)
class ProjectResourceFact:
    project_resource_id: str
    resource_id: str
    planned_hours: float
    is_active: bool


@dataclass(frozen=True, slots=True)
class LaborAssignmentFact:
    assignment_id: str
    task_id: str
    resource_id: str
    hours_logged: float


@dataclass(frozen=True, slots=True)
class ResourceFact:
    resource_id: str
    name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class FinanceSnapshotFacts:
    tenant_id: str
    organization_id: str
    project_id: str
    as_of: date
    project: FinanceProjectFact
    approved_forecast: ApprovedForecastFact | None
    control: FinanceControlFact
    tasks: tuple[TaskFact, ...]
    ledger_entries: tuple[FinanceLedgerFact, ...]
    cost_aggregates: tuple[CostAggregateFact, ...]
    project_resources: tuple[ProjectResourceFact, ...]
    assignments: tuple[LaborAssignmentFact, ...]
    resources: tuple[ResourceFact, ...]

    @property
    def ledger_entry_count(self) -> int:
        return len(self.ledger_entries)

    @property
    def distinct_cost_currencies(self) -> frozenset[str]:
        return frozenset(
            row.currency_code.strip().upper()
            for row in self.ledger_entries
            if row.currency_code and row.currency_code.strip()
        )


@dataclass(frozen=True, slots=True)
class EvmBaselineTaskFact:
    task_id: str
    baseline_start: date | None
    baseline_finish: date | None
    baseline_duration_days: int
    baseline_planned_cost: Decimal


@dataclass(frozen=True, slots=True)
class EvmSeriesFacts:
    finance: FinanceSnapshotFacts
    baseline_id: str | None
    baseline_tasks: tuple[EvmBaselineTaskFact, ...]
