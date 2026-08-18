"""Single semantic authority for the ProjectResource planned-hours envelope
invariant: ``SUM(TaskAssignment.allocated_planned_hours for a resource on a
project) <= ProjectResource.planned_hours``.

Both write paths that touch this invariant -- allocating/re-allocating a
task's planned-hours share (``application/tasks/commands/assignment.py``)
and resizing the envelope itself
(``application/resources/commands/project_resource_commands.py``) -- must
call this module rather than re-deriving the sum independently, so the rule
cannot drift between the two call sites.
"""

from __future__ import annotations

from decimal import Decimal

from src.core.platform.common.exceptions import BusinessRuleError

ENVELOPE_UNALLOCATED = "UNALLOCATED"
ENVELOPE_PARTIALLY_ALLOCATED = "PARTIALLY_ALLOCATED"
ENVELOPE_FULLY_ALLOCATED = "FULLY_ALLOCATED"
ENVELOPE_OVERALLOCATED = "OVERALLOCATED"

BURN_NOT_STARTED = "NOT_STARTED"
BURN_WITHIN_PLAN = "WITHIN_PLAN"
BURN_NEAR_PLAN = "NEAR_PLAN"
BURN_OVERRUN = "OVERRUN"

# Matches the existing 90%/"near capacity" threshold already established for
# resource utilization bands (application/resources/resource_load_engine.py),
# reused here rather than inventing a second arbitrary threshold.
_NEAR_PLAN_THRESHOLD_PERCENT = 90.0


def planned_burn_percent(*, planned_hours: Decimal, actual_hours: Decimal) -> float:
    if planned_hours <= 0:
        return 0.0
    return float(actual_hours) / float(planned_hours) * 100.0


def burn_status(*, planned_hours: Decimal, actual_hours: Decimal) -> str:
    if actual_hours <= 0:
        return BURN_NOT_STARTED
    if planned_hours <= 0:
        return BURN_OVERRUN
    percent = planned_burn_percent(planned_hours=planned_hours, actual_hours=actual_hours)
    if percent > 100.0:
        return BURN_OVERRUN
    if percent >= _NEAR_PLAN_THRESHOLD_PERCENT:
        return BURN_NEAR_PLAN
    return BURN_WITHIN_PLAN


def allocated_to_tasks_hours(
    *,
    task_repo,
    assignment_repo,
    project_id: str,
    resource_id: str,
    exclude_assignment_id: str | None = None,
) -> Decimal:
    """SUM(TaskAssignment.allocated_planned_hours) for this resource across
    every task in this project, optionally excluding one assignment (the
    one currently being re-allocated, so it isn't double-counted against
    its own proposed new value)."""
    return sum(
        (
            a.allocated_planned_hours
            for a in resource_assignments_in_project(
                task_repo=task_repo,
                assignment_repo=assignment_repo,
                project_id=project_id,
                resource_id=resource_id,
            )
            if a.id != exclude_assignment_id
        ),
        Decimal("0"),
    )


def resource_assignments_in_project(
    *, task_repo, assignment_repo, project_id: str, resource_id: str
):
    """The complete, authoritative set of this resource's TaskAssignment
    rows within this project -- one bounded round trip via the batched
    ``list_by_tasks`` reader, never a per-row loop and never limited to
    whatever page of tasks the UI currently has loaded."""
    task_ids = [t.id for t in task_repo.list_by_project(project_id)]
    if not task_ids:
        return []
    return [
        a
        for a in assignment_repo.list_by_tasks(task_ids)
        if a.resource_id == resource_id
    ]


def actual_hours_total(*, task_repo, assignment_repo, project_id: str, resource_id: str) -> Decimal:
    """SUM(TaskAssignment.hours_logged) for this resource across this
    project -- hours_logged is itself already the authoritative,
    TimeEntry-derived, all-time total per assignment, so this is the
    TimeEntry -> TaskAssignment -> ProjectResource rollup in one step."""
    return sum(
        (
            a.hours_logged
            for a in resource_assignments_in_project(
                task_repo=task_repo,
                assignment_repo=assignment_repo,
                project_id=project_id,
                resource_id=resource_id,
            )
        ),
        Decimal("0"),
    )


def envelope_status(*, planned_hours: Decimal, allocated_total: Decimal) -> str:
    if allocated_total > planned_hours:
        return ENVELOPE_OVERALLOCATED
    if planned_hours <= 0:
        return ENVELOPE_UNALLOCATED if allocated_total <= 0 else ENVELOPE_FULLY_ALLOCATED
    if allocated_total <= 0:
        return ENVELOPE_UNALLOCATED
    if allocated_total >= planned_hours:
        return ENVELOPE_FULLY_ALLOCATED
    return ENVELOPE_PARTIALLY_ALLOCATED


def require_can_allocate_task_hours(
    *,
    planned_hours: Decimal,
    allocated_total_excluding_this_task: Decimal,
    proposed_task_hours: Decimal,
    resource_id: str,
) -> Decimal:
    """Raises PROJECT_RESOURCE_HOURS_OVERALLOCATED if allocating
    ``proposed_task_hours`` to one task would push this resource's project
    total beyond the envelope. Returns the proposed new total on success."""
    proposed_total = allocated_total_excluding_this_task + proposed_task_hours
    if proposed_total > planned_hours:
        raise BusinessRuleError(
            f"Allocating {proposed_task_hours} hours to this task would bring "
            f"{resource_id}'s total allocated hours on this project to "
            f"{proposed_total}, exceeding its planned envelope of {planned_hours}.",
            code="PROJECT_RESOURCE_HOURS_OVERALLOCATED",
        )
    return proposed_total


def require_can_reduce_envelope(
    *, new_envelope: Decimal, allocated_total: Decimal
) -> None:
    """Raises PROJECT_RESOURCE_ENVELOPE_BELOW_ALLOCATIONS if shrinking the
    envelope to ``new_envelope`` would leave already-allocated task hours
    exceeding it."""
    if new_envelope < allocated_total:
        raise BusinessRuleError(
            f"Cannot reduce planned hours to {new_envelope}: "
            f"{allocated_total} hours are already allocated to tasks for this resource.",
            code="PROJECT_RESOURCE_ENVELOPE_BELOW_ALLOCATIONS",
        )


__all__ = [
    "BURN_NEAR_PLAN",
    "BURN_NOT_STARTED",
    "BURN_OVERRUN",
    "BURN_WITHIN_PLAN",
    "ENVELOPE_FULLY_ALLOCATED",
    "ENVELOPE_OVERALLOCATED",
    "ENVELOPE_PARTIALLY_ALLOCATED",
    "ENVELOPE_UNALLOCATED",
    "actual_hours_total",
    "allocated_to_tasks_hours",
    "burn_status",
    "envelope_status",
    "planned_burn_percent",
    "require_can_allocate_task_hours",
    "require_can_reduce_envelope",
    "resource_assignments_in_project",
]
