from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ResourceWorkloadDayResponse:
    work_date: date
    base_capacity_hours: Decimal
    effective_capacity_hours: Decimal
    planned_commitment_hours: Decimal
    remaining_capacity_hours: Decimal
    utilization_percent: Decimal | None
    overallocated: bool
    assignment_count: int


@dataclass(frozen=True, slots=True)
class ResourceWorkloadResponse:
    resource_id: str
    start_date: date
    end_date: date
    calendar_source_chain: tuple[str, ...]
    capacity_percent: Decimal
    base_capacity_hours: Decimal
    effective_capacity_hours: Decimal
    planned_commitment_hours: Decimal
    allocated_planned_hours: Decimal
    remaining_capacity_hours: Decimal
    utilization_percent: Decimal | None
    overallocated: bool
    conflict_dates: tuple[date, ...]
    project_count: int
    assignment_count: int
    resource_version: int
    days: tuple[ResourceWorkloadDayResponse, ...]


