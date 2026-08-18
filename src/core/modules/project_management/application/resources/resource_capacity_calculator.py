"""Resource capacity calculator — derives capacity summary from calendar rules.

Capacity is NEVER stored. This service computes it on demand from resolved
calendar contexts. Caller injects assigned hours to get utilization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from src.core.platform.application.time_management.calendar.capacity.enterprise_calendar_resolver import (
    ResolvedCalendarContext,
)
from src.core.modules.project_management.application.resources.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)


@dataclass
class ResourceCapacitySummary:
    resource_id: str
    start: date
    end: date
    base_hours: float
    available_hours: float
    assigned_hours: float
    remaining_hours: float
    capacity_percent: float
    utilization_percent: float
    working_days: int
    unavailable_days: int
    conflicts: list[str]
    source_chain: list[str]
    days: list[ResolvedCalendarContext] = field(default_factory=list)

    @property
    def is_overallocated(self) -> bool:
        return self.assigned_hours > self.available_hours


class ResourceCapacityCalculator:
    """
    Derives capacity summary for a resource over a date range.
    Does NOT persist capacity_percent.
    """

    def __init__(
        self,
        availability_service: EnterpriseResourceAvailabilityService,
    ) -> None:
        self._availability = availability_service

    def compute(
        self,
        resource_id: str,
        start: date,
        end: date,
        *,
        project_id: str | None = None,
        site_id: str | None = None,
        department_id: str | None = None,
        assigned_hours_by_date: dict[date, float] | None = None,
    ) -> ResourceCapacitySummary:
        days = self._availability.get_availability_range(
            resource_id,
            project_id=project_id,
            site_id=site_id,
            department_id=department_id,
            start=start,
            end=end,
            assigned_hours_by_date=assigned_hours_by_date,
        )

        base_total = sum(d.base_hours for d in days)
        available_total = sum(d.available_hours for d in days)
        assigned_total = sum(d.assigned_hours for d in days)
        remaining_total = max(0.0, available_total - assigned_total)
        working_days = sum(1 for d in days if d.base_hours > 0)
        unavailable_days = sum(1 for d in days if d.available_hours <= 0)

        capacity_pct = (
            round(available_total / base_total * 100, 2) if base_total > 0 else 0.0
        )
        utilization_pct = (
            round(assigned_total / available_total * 100, 2) if available_total > 0 else 0.0
        )

        conflicts = []
        for d in days:
            if d.assigned_hours > d.available_hours:
                conflicts.append(
                    f"{d.date}: assigned {d.assigned_hours:.1f}h > available {d.available_hours:.1f}h"
                )

        source_chain = (
            days[0].source_chain if days else []
        )

        return ResourceCapacitySummary(
            resource_id=resource_id,
            start=start,
            end=end,
            base_hours=round(base_total, 4),
            available_hours=round(available_total, 4),
            assigned_hours=round(assigned_total, 4),
            remaining_hours=round(remaining_total, 4),
            capacity_percent=capacity_pct,
            utilization_percent=utilization_pct,
            working_days=working_days,
            unavailable_days=unavailable_days,
            conflicts=conflicts,
            source_chain=source_chain,
            days=days,
        )


def compute_resource_capacity_from_assignments(
    calculator: ResourceCapacityCalculator,
    *,
    resource_id: str,
    task_repo,
    assignment_repo,
    start: date,
    end: date,
    project_id: str | None = None,
    site_id: str | None = None,
    department_id: str | None = None,
) -> ResourceCapacitySummary:
    """Real assigned-hours derivation for the resource-level calendar
    capacity display: `ResourceCapacityCalculator.compute()` requires the
    caller to supply `assigned_hours_by_date` -- nothing did, which is why
    this display was always empty in production. This derives it from the
    resource's real TaskAssignment rows (allocation_percent x that day's
    own calendar-resolved base_hours, for every day a task's schedule
    window covers), rather than leaving it at an implicit zero.

    Two-pass: first resolve the calendar with no assigned hours (to learn
    each day's real base_hours), then resolve again with the real
    allocation-weighted assigned hours filled in. Both passes hit the same
    cached calendar resolution (EnterpriseCalendarResolver caches per
    calendar id), so this is not a second independent full recomputation
    of calendar rules.
    """
    baseline = calculator.compute(
        resource_id, start, end,
        project_id=project_id, site_id=site_id, department_id=department_id,
    )
    base_hours_by_date = {day.date: day.base_hours for day in baseline.days}

    assignments = [
        a for a in assignment_repo.list_by_resource(resource_id)
        if a.allocation_percent and a.allocation_percent > 0
    ]
    task_ids = list({a.task_id for a in assignments})
    tasks_by_id = {t.id: t for t in task_repo.list_by_ids(task_ids)} if task_ids else {}

    assigned_hours_by_date: dict[date, float] = {}
    for assignment in assignments:
        task = tasks_by_id.get(assignment.task_id)
        if task is None:
            continue
        task_start = getattr(task, "start_date", None) or getattr(task, "actual_start", None)
        task_end = getattr(task, "end_date", None) or getattr(task, "actual_end", None)
        if not task_start or not task_end:
            continue
        window_start = max(start, task_start)
        window_end = min(end, task_end)
        current = window_start
        while current <= window_end:
            day_base_hours = base_hours_by_date.get(current, 0.0)
            if day_base_hours > 0:
                contribution = day_base_hours * (float(assignment.allocation_percent) / 100.0)
                assigned_hours_by_date[current] = assigned_hours_by_date.get(current, 0.0) + contribution
            current = current + timedelta(days=1)

    return calculator.compute(
        resource_id, start, end,
        project_id=project_id, site_id=site_id, department_id=department_id,
        assigned_hours_by_date=assigned_hours_by_date,
    )


__all__ = [
    "ResourceCapacityCalculator",
    "ResourceCapacitySummary",
    "compute_resource_capacity_from_assignments",
]
