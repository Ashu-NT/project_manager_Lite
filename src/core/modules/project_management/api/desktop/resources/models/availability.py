from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceAvailabilityDayDto:
    work_date: str
    date_label: str
    base_capacity_hours: float
    effective_capacity_hours: float
    planned_commitment_hours: float
    remaining_capacity_hours: float
    utilization_percent: float | None
    utilization_label: str
    overallocated: bool
    assignment_count: int


@dataclass(frozen=True)
class ResourceAvailabilityDto:
    resource_id: str
    start_date: str
    end_date: str
    from_date_label: str
    to_date_label: str
    calendar_source_label: str
    capacity_percent: float
    base_capacity_hours: float
    effective_capacity_hours: float
    planned_commitment_hours: float
    allocated_planned_hours: float
    remaining_capacity_hours: float
    utilization_percent: float | None
    utilization_label: str
    overallocated: bool
    conflict_days: int
    project_count: int
    assignment_count: int
    days: tuple[ResourceAvailabilityDayDto, ...]


__all__ = ["ResourceAvailabilityDayDto", "ResourceAvailabilityDto"]
