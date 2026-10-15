from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    UnresolvedLaborRate,
)


@dataclass(frozen=True)
class ProjectFinanceLedgerRow:
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


@dataclass
class LaborAssignmentRow:
    assignment_id: str
    task_id: str
    task_name: str
    hours: Decimal
    hourly_rate: Decimal
    currency_code: str | None
    cost: Decimal


@dataclass
class LaborResourceRow:
    resource_id: str
    resource_name: str
    total_hours: Decimal
    hourly_rate: Decimal
    currency_code: str | None
    total_cost: Decimal
    assignments: list[LaborAssignmentRow]


@dataclass(frozen=True)
class PlannedLaborResourceRow:
    project_resource_id: str
    resource_id: str
    resource_name: str
    planned_hours: Decimal
    hourly_rate: Decimal
    currency_code: str | None
    total_cost: Decimal


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


__all__ = ['ProjectFinanceLedgerRow', 'CostSourceRow', 'CostSourceBreakdown', 'CostBreakdownRow', 'LaborAssignmentRow', 'LaborResourceRow', 'PlannedLaborResourceRow', 'LaborDetailsResult']
