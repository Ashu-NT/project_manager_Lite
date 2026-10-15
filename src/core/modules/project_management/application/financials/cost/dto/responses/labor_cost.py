from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    UnresolvedLaborRate,
)


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


__all__ = ['LaborAssignmentRow', 'LaborResourceRow', 'PlannedLaborResourceRow', 'LaborDetailsResult']
