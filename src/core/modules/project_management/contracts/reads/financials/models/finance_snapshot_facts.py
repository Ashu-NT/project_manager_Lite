"""Immutable database facts used to compose a finance snapshot.

These types deliberately contain no policy-applied totals, ORM rows, domain
entities, permission decisions, or desktop DTOs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class FinanceProjectFact:
    project_id: str
    tenant_id: str
    organization_id: str
    currency: str | None
    planned_budget: float
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
class CostItemFact:
    cost_item_id: str
    task_id: str | None
    description: str
    cost_type: str
    currency_code: str | None
    planned_amount: float
    committed_amount: float
    actual_amount: float
    forecast_amount: float | None
    commitment_status: str
    incurred_date: date | None


@dataclass(frozen=True, slots=True)
class CostAggregateFact:
    """Stored cost totals grouped without applying labor-source policy."""

    cost_type: str
    currency_code: str | None
    commitment_status: str
    positive_planned: float
    positive_committed: float
    positive_actual_as_of: float
    raw_planned: float
    raw_committed: float
    raw_actual_as_of: float
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
    cost_items: tuple[CostItemFact, ...]
    cost_aggregates: tuple[CostAggregateFact, ...]
    project_resources: tuple[ProjectResourceFact, ...]
    assignments: tuple[LaborAssignmentFact, ...]
    resources: tuple[ResourceFact, ...]

    @property
    def cost_item_count(self) -> int:
        return len(self.cost_items)

    @property
    def distinct_cost_currencies(self) -> frozenset[str]:
        return frozenset(
            row.currency_code.strip().upper()
            for row in self.cost_items
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
