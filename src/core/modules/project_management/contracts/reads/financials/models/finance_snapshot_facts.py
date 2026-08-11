"""Immutable canonical database facts used to compose finance snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class FinanceProjectFact:
    project_id: str
    tenant_id: str
    organization_id: str
    currency_code: str
    approved_budget: float
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
    amount: float
    occurred_on: date | None


@dataclass(frozen=True, slots=True)
class CostAggregateFact:
    """Canonical financial totals grouped by stage, type, and currency."""

    stage: str
    cost_type: str
    currency_code: str | None
    total_amount: float
    row_count: int


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
    baseline_planned_cost: float


@dataclass(frozen=True, slots=True)
class EvmSeriesFacts:
    finance: FinanceSnapshotFacts
    baseline_id: str | None
    baseline_tasks: tuple[EvmBaselineTaskFact, ...]
