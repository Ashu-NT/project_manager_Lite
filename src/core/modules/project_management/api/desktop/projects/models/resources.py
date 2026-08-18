from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectResourceDesktopDto:
    id: str
    project_id: str
    resource_id: str
    resource_name: str
    role: str
    worker_type_label: str
    hourly_rate: str | None
    hourly_rate_label: str
    currency_code: str | None
    planned_hours: str
    planned_hours_label: str
    is_active: bool
    status_label: str
    version: int = 1


@dataclass(frozen=True)
class ProjectAssignableResourceOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class ProjectResourceUsageDesktopDto:
    """Desktop-facing serialization of ProjectResourceUsageFact -- see
    docs §43/§80 for the planned/allocated/unallocated/actual/remaining
    reconciliation semantics."""

    project_resource_id: str
    project_id: str
    resource_id: str
    planned_hours_label: str
    allocated_to_tasks_hours_label: str
    unallocated_planned_hours_label: str
    actual_hours_label: str
    remaining_project_hours_label: str
    planned_burn_percent: float
    task_assignment_count: int
    envelope_status: str
    envelope_status_label: str
    burn_status: str
    burn_status_label: str
    version: int


__all__ = [
    "ProjectAssignableResourceOptionDescriptor",
    "ProjectResourceDesktopDto",
    "ProjectResourceUsageDesktopDto",
]
