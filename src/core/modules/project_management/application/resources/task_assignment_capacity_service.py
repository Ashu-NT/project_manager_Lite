"""Authoritative calendar-based capacity for Task Assignment availability
preview and overallocation validation (docs §44's capacity-authority
migration).

Composition, and why: `EnterpriseCalendarResolver` (platform) already
resolves real working-day hours through the org/site/department/employee/
project/resource precedence chain; `EnterpriseResourceAvailabilityService`
(PM) already wraps that resolver cleanly. Neither of those, nor
`ResourceCapacityCalculator` (which wraps the availability service for the
Resources-workspace calendar display), ever multiplied in
`Resource.capacity_percent` -- confirmed by reading both, not assumed -- so
this module is the first place that formula (effective_available_capacity
= calendar_available_hours * capacity_percent / 100) is actually applied.
It also builds real, per-day existing/proposed committed-hours facts from
actual TaskAssignment data, which none of the four existing calculators do
for this specific "is this proposed task assignment capacity-safe" question.

Resource Detail's multi-project workload view now uses its own bounded reader
and the same enterprise calendar adapter. `ResourceLoadEngine` and
`PortfolioResourcePoolService` remain distinct set-based projection tools for
Dashboard/Scheduling KPIs and portfolio capacity. See docs §44 for the full
accounting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

CAPACITY_AVAILABLE = "AVAILABLE"
CAPACITY_NEAR_CAPACITY = "NEAR_CAPACITY"
CAPACITY_OVER_CAPACITY = "OVER_CAPACITY"
CAPACITY_UNKNOWN = "UNKNOWN"

# Matches the existing 90% "near capacity" threshold already established in
# application/resources/resource_load_engine.py -- reused rather than
# inventing a second arbitrary threshold, per the request's own instruction.
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
    """Authoritative capacity result for one resource's proposed (or edited)
    commitment across [start_date, end_date] -- the effective interval is
    always the Task's own start_date/end_date (see docs §44 §8: TaskAssignment
    has no independent dates, and none were added for this)."""

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
    """Real assignment commitments (§9/§10): existing = this resource's
    OTHER assignments within the SAME project overlapping [start_date,
    end_date] (matching the scope the pre-migration validator already used
    -- this migration changes the CALCULATION, not the scope), excluding
    `exclude_assignment_id` when editing. Proposed = `proposed_allocation_percent`
    applied across the full requested interval (the new/edited assignment's
    own task window). Batched: one `list_by_resource` + one `list_by_ids`
    call, never a per-task loop (§9/§26)."""
    resource = resource_repo.get(resource_id)
    capacity_modifier = Decimal(str(getattr(resource, "capacity_percent", 100.0) or 100.0)) / Decimal("100")
    if capacity_modifier <= 0:
        capacity_modifier = Decimal("1")

    raw_days = availability_service.get_availability_range(
        resource_id,
        project_id=project_id,
        start=start_date,
        end=end_date,
    )
    effective_by_date: dict[date, Decimal | None] = {}
    # Raw (unscaled) calendar hours -- the base against which allocation_percent
    # commitments are measured. capacity_percent narrows the AVAILABLE ceiling
    # (effective_by_date) only; it must not also shrink the committed-hours
    # numerator, or the two scale together and capacity_percent cancels out of
    # the ratio entirely.
    raw_available_by_date: dict[date, Decimal] = {}
    source_chain: tuple[str, ...] = ()
    calendar_capacity_hours = Decimal("0")
    for day in raw_days:
        calendar_capacity_hours += Decimal(str(day.base_hours))
        if not day.source_chain:
            # No calendar could be resolved at all for this day -- explicit
            # UNKNOWN, never a false "0h available" overload trigger (§24).
            effective_by_date[day.date] = None
            continue
        raw_hours = Decimal(str(day.available_hours))
        raw_available_by_date[day.date] = raw_hours
        effective_by_date[day.date] = raw_hours * capacity_modifier
        if not source_chain:
            source_chain = tuple(day.source_chain)

    project_task_ids = {t.id for t in task_repo.list_by_project(project_id)}
    assignments = [
        a
        for a in assignment_repo.list_by_resource(resource_id)
        if a.task_id in project_task_ids and a.id != exclude_assignment_id
    ]
    other_task_ids = list({a.task_id for a in assignments})
    tasks_by_id = {t.id: t for t in task_repo.list_by_ids(other_task_ids)} if other_task_ids else {}

    existing_by_date: dict[date, Decimal] = {}
    contributing_by_date: dict[date, set[str]] = {}
    for assignment in assignments:
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
        allocation_fraction = Decimal(str(assignment.allocation_percent or 0)) / Decimal("100")
        current = overlap_start
        while current <= overlap_end:
            raw = raw_available_by_date.get(current)
            if raw is not None:
                existing_by_date[current] = existing_by_date.get(current, Decimal("0")) + (
                    raw * allocation_fraction
                )
                contributing_by_date.setdefault(current, set()).add(assignment.task_id)
            current += timedelta(days=1)

    proposed_fraction = Decimal(str(proposed_allocation_percent or 0)) / Decimal("100")
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
        existing = existing_by_date.get(current, Decimal("0"))
        proposed = proposed_by_date.get(current, Decimal("0"))
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

    known_days = [d for d in days if d.effective_available_capacity_hours is not None]
    return TaskAssignmentCapacityFact(
        resource_id=resource_id,
        start_date=start_date,
        end_date=end_date,
        calendar_capacity_hours=calendar_capacity_hours,
        effective_available_capacity_hours=(
            sum((d.effective_available_capacity_hours for d in known_days), Decimal("0"))
            if known_days
            else None
        ),
        existing_committed_capacity_hours=sum(existing_by_date.values(), Decimal("0")),
        proposed_committed_capacity_hours=sum(proposed_by_date.values(), Decimal("0")),
        resulting_committed_capacity_hours=sum(
            (d.resulting_committed_capacity_hours for d in days), Decimal("0")
        ),
        peak_utilization_percent=peak_percent,
        capacity_status=_overall_status([d.status for d in days]),
        conflict_dates=tuple(conflict_dates),
        source_chain=source_chain,
        days=tuple(days),
    )


__all__ = [
    "CAPACITY_AVAILABLE",
    "CAPACITY_NEAR_CAPACITY",
    "CAPACITY_OVER_CAPACITY",
    "CAPACITY_UNKNOWN",
    "DailyCapacityCommitment",
    "TaskAssignmentCapacityFact",
    "evaluate_task_assignment_capacity",
]
