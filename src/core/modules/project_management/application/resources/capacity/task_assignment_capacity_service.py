"""Authoritative calendar-based capacity for Task Assignment availability preview and
overallocation validation.

`effective_available_capacity = calendar_available_hours * capacity_percent / 100` -- the
only place `capacity_percent` is applied this way; `ResourceCapacityCalculator` and the other
resource calculators never multiply by it. Builds real, per-day existing/proposed
committed-hours facts from actual TaskAssignment data. `ResourceLoadEngine` and
`PortfolioResourcePoolQueryHandler` remain distinct set-based projection tools for
Dashboard/Scheduling KPIs and portfolio capacity -- this module answers a different question:
whether one proposed assignment is capacity-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal

from src.core.modules.project_management.application.resources.capacity.queries.availability import (
    ResourceAvailabilityQueryHandler,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment
from src.core.platform.application.time_management.calendar.capacity.global_calendar_shim import (
    end_date_from_working_dates,
    working_day_search_end,
)
from src.core.platform.application.time_management.calendar.capacity.platform_calendar_resolver import (
    ResolvedCalendarContext,
)
from src.core.platform.common.exceptions import NotFoundError

CAPACITY_AVAILABLE = "AVAILABLE"
CAPACITY_NEAR_CAPACITY = "NEAR_CAPACITY"
CAPACITY_OVER_CAPACITY = "OVER_CAPACITY"
CAPACITY_UNKNOWN = "UNKNOWN"

# Matches the 90% "near capacity" threshold in resource_load_engine.py -- reused
# rather than inventing a second arbitrary threshold.
_NEAR_CAPACITY_THRESHOLD_PERCENT = 90.0


@dataclass(frozen=True)
class DailyCapacityCommitment:
    date: date
    effective_available_capacity_hours: Decimal | None  # None == UNKNOWN (no calendar resolved)
    existing_committed_capacity_hours: Decimal
    proposed_committed_capacity_hours: Decimal
    resulting_committed_capacity_hours: Decimal
    contributing_task_ids: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class TaskAssignmentCapacityFact:
    """Authoritative capacity result for one resource's proposed (or edited) commitment
    across [start_date, end_date] -- always the Task's own start_date/end_date;
    TaskAssignment has no independent dates."""

    resource_id: str
    start_date: date
    end_date: date
    calendar_capacity_hours: Decimal
    effective_available_capacity_hours: Decimal | None
    existing_committed_capacity_hours: Decimal
    proposed_committed_capacity_hours: Decimal
    resulting_committed_capacity_hours: Decimal
    peak_utilization_percent: float | None
    capacity_status: str
    conflict_dates: tuple[date, ...]
    source_chain: tuple[str, ...]
    days: tuple[DailyCapacityCommitment, ...]

    @property
    def is_over_capacity(self) -> bool:
        return self.capacity_status == CAPACITY_OVER_CAPACITY


def _day_status(*, effective_hours: Decimal | None, resulting_hours: Decimal) -> str:
    if effective_hours is None:
        return CAPACITY_UNKNOWN
    if effective_hours <= 0:
        return CAPACITY_OVER_CAPACITY if resulting_hours > 0 else CAPACITY_AVAILABLE
    percent = float(resulting_hours) / float(effective_hours) * 100.0
    if percent > 100.0 + 1e-9:
        return CAPACITY_OVER_CAPACITY
    if percent >= _NEAR_CAPACITY_THRESHOLD_PERCENT:
        return CAPACITY_NEAR_CAPACITY
    return CAPACITY_AVAILABLE


def _overall_status(statuses: list[str]) -> str:
    if CAPACITY_OVER_CAPACITY in statuses:
        return CAPACITY_OVER_CAPACITY
    if CAPACITY_NEAR_CAPACITY in statuses:
        return CAPACITY_NEAR_CAPACITY
    if statuses and all(s == CAPACITY_UNKNOWN for s in statuses):
        return CAPACITY_UNKNOWN
    return CAPACITY_AVAILABLE


def evaluate_task_assignment_capacity(
    *,
    resource_id: str,
    project_id: str,
    start_date: date,
    end_date: date,
    proposed_allocation_percent: float,
    task_repo,
    assignment_repo,
    resource_repo,
    availability_service,
    exclude_assignment_id: str | None = None,
) -> TaskAssignmentCapacityFact:
    """Existing = this resource's OTHER assignments within the SAME project overlapping
    [start_date, end_date], excluding `exclude_assignment_id` when editing. Proposed =
    `proposed_allocation_percent` applied across the full requested interval (the
    new/edited assignment's own task window). Reads project tasks and resource
    assignments in sets, never a per-task query loop."""
    resource = resource_repo.get(resource_id)
    raw_days = availability_service.get_availability_range(
        resource_id,
        project_id=project_id,
        start=start_date,
        end=end_date,
    )
    tasks_by_id = {task.id: task for task in task_repo.list_by_project(project_id)}
    assignments = assignment_repo.list_by_resource(resource_id)
    return calculate_task_assignment_capacity(
        resource_id=resource_id, resource=resource, start_date=start_date, end_date=end_date,
        proposed_allocation_percent=proposed_allocation_percent, raw_days=raw_days,
        assignments=assignments, tasks_by_id=tasks_by_id, exclude_assignment_id=exclude_assignment_id,
    )


def calculate_task_assignment_capacity(
    *, resource_id: str, resource: Resource | None, start_date: date, end_date: date,
    proposed_allocation_percent: float, raw_days: list[ResolvedCalendarContext],
    assignments: list[TaskAssignment], tasks_by_id: dict[str, Task],
    exclude_assignment_id: str | None = None,
) -> TaskAssignmentCapacityFact:
    """Query-free calculation shared by single previews and batch response reads.

    tasks_by_id contains only tasks in the requested project.
    """
    capacity_modifier = Decimal(str(getattr(resource, "capacity_percent", 100.0) or 100.0)) / Decimal(100)
    if capacity_modifier <= 0:
        capacity_modifier = Decimal(1)
    effective_by_date: dict[date, Decimal | None] = {}
    # Raw (unscaled) hours: capacity_percent must narrow the available ceiling only,
    # never the committed-hours numerator too, or the two scale together and it
    # cancels out of the ratio.
    raw_available_by_date: dict[date, Decimal] = {}
    source_chain: tuple[str, ...] = ()
    calendar_capacity_hours = Decimal(0)
    for day in raw_days:
        calendar_capacity_hours += Decimal(str(day.base_hours))
        if not day.source_chain:
            # No calendar could be resolved for this day -- explicit UNKNOWN, never a
            # false "0h available" overload trigger.
            effective_by_date[day.date] = None
            continue
        raw_hours = Decimal(str(day.available_hours))
        raw_available_by_date[day.date] = raw_hours
        effective_by_date[day.date] = raw_hours * capacity_modifier
        if not source_chain:
            source_chain = tuple(day.source_chain)

    existing_by_date: dict[date, Decimal] = {}
    contributing_by_date: dict[date, set[str]] = {}
    for assignment in assignments:
        if assignment.resource_id != resource_id or assignment.id == exclude_assignment_id:
            continue
        task = tasks_by_id.get(assignment.task_id)
        if task is None:
            continue
        task_start = getattr(task, "start_date", None)
        task_end = getattr(task, "end_date", None)
        if not task_start or not task_end:
            continue
        overlap_start = max(start_date, task_start)
        overlap_end = min(end_date, task_end)
        if overlap_end < overlap_start:
            continue
        allocation_fraction = Decimal(str(assignment.allocation_percent or 0)) / Decimal(100)
        current = overlap_start
        while current <= overlap_end:
            raw = raw_available_by_date.get(current)
            if raw is not None:
                existing_by_date[current] = existing_by_date.get(current, Decimal(0)) + (
                    raw * allocation_fraction
                )
                contributing_by_date.setdefault(current, set()).add(assignment.task_id)
            current += timedelta(days=1)

    proposed_fraction = Decimal(str(proposed_allocation_percent or 0)) / Decimal(100)
    proposed_by_date: dict[date, Decimal] = {}
    current = start_date
    while current <= end_date:
        raw = raw_available_by_date.get(current)
        if raw is not None:
            proposed_by_date[current] = raw * proposed_fraction
        current += timedelta(days=1)

    days: list[DailyCapacityCommitment] = []
    conflict_dates: list[date] = []
    peak_percent: float | None = None
    current = start_date
    while current <= end_date:
        effective = effective_by_date.get(current)
        existing = existing_by_date.get(current, Decimal(0))
        proposed = proposed_by_date.get(current, Decimal(0))
        resulting = existing + proposed
        status = _day_status(effective_hours=effective, resulting_hours=resulting)
        if status == CAPACITY_OVER_CAPACITY:
            conflict_dates.append(current)
        if effective is not None and effective > 0:
            percent = float(resulting) / float(effective) * 100.0
            peak_percent = percent if peak_percent is None else max(peak_percent, percent)
        days.append(
            DailyCapacityCommitment(
                date=current,
                effective_available_capacity_hours=effective,
                existing_committed_capacity_hours=existing,
                proposed_committed_capacity_hours=proposed,
                resulting_committed_capacity_hours=resulting,
                contributing_task_ids=tuple(sorted(contributing_by_date.get(current, ()))),
                status=status,
            )
        )
        current += timedelta(days=1)

    known_hours = [
        hours
        for day in days
        if (hours := day.effective_available_capacity_hours) is not None
    ]
    return TaskAssignmentCapacityFact(
        resource_id=resource_id,
        start_date=start_date,
        end_date=end_date,
        calendar_capacity_hours=calendar_capacity_hours,
        effective_available_capacity_hours=(
            sum(known_hours, Decimal(0))
            if known_hours
            else None
        ),
        existing_committed_capacity_hours=sum(existing_by_date.values(), Decimal(0)),
        proposed_committed_capacity_hours=sum(proposed_by_date.values(), Decimal(0)),
        resulting_committed_capacity_hours=sum(
            (d.resulting_committed_capacity_hours for d in days), Decimal(0)
        ),
        peak_utilization_percent=peak_percent,
        capacity_status=_overall_status([d.status for d in days]),
        conflict_dates=tuple(conflict_dates),
        source_chain=source_chain,
        days=tuple(days),
    )


def enrich_task_assignment_capacities(
    *, task: Task, assignments: list[TaskAssignment], resources: list[Resource],
    task_repo: TaskRepository, assignment_repo: AssignmentRepository,
    availability_service: ResourceAvailabilityQueryHandler,
) -> dict[str, TaskAssignmentCapacityFact]:
    """One project/task/assignment snapshot and one batch calendar read, never row queries."""
    if not task.start_date or (task.end_date is None and task.duration_days is None):
        return {}
    tasks = {row.id: row for row in task_repo.list_by_project(task.project_id)}
    tasks[task.id] = task
    for milestone in list(tasks.values()):
        if milestone.start_date and milestone.end_date is None and milestone.duration_days == 0:
            tasks[milestone.id] = replace(milestone, end_date=milestone.start_date)
    derived = [row for row in tasks.values()
               if row.start_date and row.end_date is None and row.duration_days is not None]
    if derived:
        start = min(row.start_date for row in derived if row.start_date is not None)
        end = max(working_day_search_end(row.start_date, int(row.duration_days or 0))
                  for row in derived if row.start_date is not None)
        working_dates = availability_service.get_scheduling_working_dates(start, end)
        for row in derived:
            assert row.start_date is not None
            end_date = end_date_from_working_dates(row.start_date, int(row.duration_days or 0), working_dates)
            tasks[row.id] = replace(row, end_date=end_date)
    current = tasks[task.id]
    if current.start_date is None or current.end_date is None:
        return {}
    resource_ids = {row.resource_id for row in assignments}
    selected = [resource for resource in resources if resource.id in resource_ids]
    missing = resource_ids - {resource.id for resource in selected}
    if missing:
        raise NotFoundError(f"Resource '{min(missing)}' not found.", code="RESOURCE_NOT_FOUND")
    project_assignments = assignment_repo.list_by_tasks(list(tasks))
    assignments_by_resource: dict[str, list[TaskAssignment]] = {}
    for assignment in project_assignments:
        assignments_by_resource.setdefault(assignment.resource_id, []).append(assignment)
    days = availability_service.get_availability_ranges(
        selected, project_id=task.project_id, start=current.start_date, end=current.end_date,
    )
    resources_by_id = {resource.id: resource for resource in selected}
    return {
        row.id: calculate_task_assignment_capacity(
            resource_id=row.resource_id, resource=resources_by_id[row.resource_id],
            start_date=current.start_date, end_date=current.end_date,
            proposed_allocation_percent=row.allocation_percent, raw_days=days[row.resource_id],
            assignments=assignments_by_resource.get(row.resource_id, []), tasks_by_id=tasks,
            exclude_assignment_id=row.id,
        ) for row in assignments
    }


__all__ = [
    "CAPACITY_AVAILABLE",
    "CAPACITY_NEAR_CAPACITY",
    "CAPACITY_OVER_CAPACITY",
    "CAPACITY_UNKNOWN",
    "DailyCapacityCommitment",
    "TaskAssignmentCapacityFact",
    "calculate_task_assignment_capacity",
    "enrich_task_assignment_capacities",
    "evaluate_task_assignment_capacity",
]
