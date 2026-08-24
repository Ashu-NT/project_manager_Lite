from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ResourceWorkloadDemandFact:
    assignment_id: str
    task_id: str
    project_id: str
    task_start: date
    task_end: date
    allocation_percent: Decimal
    allocated_planned_hours: Decimal


class ResourceWorkloadDemandReader(Protocol):
    def read_overlapping_assignments(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
        start_date: date,
        end_date: date,
    ) -> tuple[ResourceWorkloadDemandFact, ...]: ...


__all__ = ["ResourceWorkloadDemandFact", "ResourceWorkloadDemandReader"]
