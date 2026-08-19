"""Task Detail -> Schedule Impact: current-state schedule facts.

This is orchestration over the canonical CPM output
(``pure_cpm.run_cpm``/``CPMTaskInfo``) plus the already-canonical
``ConstraintValidator``/``find_dependency_actual_variances`` facts -- it
introduces no new scheduling math. It answers "what is this task's current
schedule position, what drives it, and how exposed is the downstream
network" without running any hypothetical simulation (that is
``ScheduleChangeImpactService.analyse``'s job).

See docs/pm_modernization/R4_4_TASK_DEPENDENCY_IMPLEMENTATION_SUMMARY.md,
"Task Detail -> Schedule Impact" section, for the product rationale.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    DependencyConstraintConflict,
)
from src.core.modules.project_management.application.scheduling.cpm.dependency_schedule_math import (
    successor_boundary,
    successor_earliest_start_from_boundary,
)
from src.core.modules.project_management.application.scheduling.cpm.dependency_actual_variance import (
    DependencyActualVariance,
)
from src.core.modules.project_management.application.scheduling.models.cpm import CPMTaskInfo
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency


@dataclass(frozen=True, slots=True)
class ScheduleDriver:
    """One authoritative fact currently constraining a task's computed
    dates -- an incoming dependency, a hard scheduling constraint, or an
    already-recorded actual date. Purely explanatory; never itself a
    computation."""

    kind: str  # "predecessor" | "constraint" | "actual_start" | "actual_finish"
    label: str
    detail: str


@dataclass(frozen=True, slots=True)
class DownstreamExposure:
    """How much of the dependency network sits downstream of a task --
    NOT a claim that all of it will move, just what is structurally
    reachable (§11)."""

    direct_successor_count: int
    downstream_task_count: int
    downstream_milestone_count: int
    critical_downstream_count: int


@dataclass(frozen=True, slots=True)
class TaskScheduleOverview:
    task_id: str
    is_available: bool
    current_start: date | None = None
    current_finish: date | None = None
    is_critical: bool = False
    total_float_days: int | None = None
    free_float_days: int | None = None
    baseline_finish: date | None = None
    schedule_variance_days: int | None = None
    drivers: tuple[ScheduleDriver, ...] = field(default_factory=tuple)
    dependency_conflicts: tuple[DependencyConstraintConflict, ...] = field(default_factory=tuple)
    actual_variances: tuple[DependencyActualVariance, ...] = field(default_factory=tuple)
    downstream: DownstreamExposure = field(
        default_factory=lambda: DownstreamExposure(0, 0, 0, 0)
    )


def _is_milestone(task: Task) -> bool:
    """The same predicate the CPM engine itself uses to branch into
    ``compute_milestone_dates`` -- not a separately-invented definition."""
    return int(getattr(task, "duration_days", 0) or 0) <= 0


def build_successors_by_task_id(deps: list[TaskDependency]) -> dict[str, set[str]]:
    successors: dict[str, set[str]] = {}
    for dep in deps:
        successors.setdefault(dep.predecessor_task_id, set()).add(dep.successor_task_id)
    return successors


def compute_free_float_days(
    task_id: str,
    cpm_result: dict[str, CPMTaskInfo],
    deps: list[TaskDependency],
    calendar: CalendarProtocol,
) -> int | None:
    """Free float: how many working days this task's finish could slip
    without delaying any direct successor's own current earliest start.

    Only computed when every direct successor edge is Finish-to-Start --
    the only case where "successor's ES minus my EF" is unambiguous. A
    task with a non-FS successor (SS/FF/SF relate a different date pair)
    reports free float as unavailable rather than showing an approximate
    or potentially-wrong number (no invented values). A task with zero
    successors can float up to whatever the project itself allows, so
    free float equals total float in that case.
    """
    info = cpm_result.get(task_id)
    if info is None or info.earliest_finish is None:
        return None
    successor_edges = [d for d in deps if d.predecessor_task_id == task_id]
    if not successor_edges:
        return info.total_float_days
    if any(d.dependency_type.value != "FS" for d in successor_edges):
        return None
    candidates: list[int] = []
    for dep in successor_edges:
        successor_info = cpm_result.get(dep.successor_task_id)
        if successor_info is None or successor_info.earliest_start is None:
            return None
        boundary = successor_boundary(
            calendar,
            dependency_type=dep.dependency_type,
            lag_days=int(dep.lag_days or 0),
            predecessor_earliest_start=info.earliest_start,
            predecessor_earliest_finish=info.earliest_finish,
        )
        if boundary is None:
            return None
        implied_earliest_start = successor_earliest_start_from_boundary(
            calendar,
            boundary,
            successor_duration_days=0,
        )
        if successor_info.earliest_start < implied_earliest_start:
            # Should not happen in a consistent forward-pass result -- this
            # edge's own boundary can never be later than the successor's
            # actual ES. Treat as no slack rather than a negative float.
            candidates.append(0)
            continue
        days = calendar.working_days_between(implied_earliest_start, successor_info.earliest_start) - 1
        candidates.append(max(0, days))
    return min(candidates) if candidates else info.total_float_days


def compute_downstream_exposure(
    task_id: str,
    tasks_by_id: dict[str, Task],
    successors_by_task_id: dict[str, set[str]],
    critical_task_ids: set[str],
) -> DownstreamExposure:
    """Breadth-first traversal over the already-loaded, in-memory
    successors map -- no per-task repository calls (§25)."""
    direct = successors_by_task_id.get(task_id, set())
    visited: set[str] = set()
    frontier = list(direct)
    while frontier:
        current = frontier.pop()
        if current in visited or current == task_id:
            continue
        visited.add(current)
        frontier.extend(successors_by_task_id.get(current, set()) - visited)
    downstream_milestones = sum(
        1 for tid in visited if tid in tasks_by_id and _is_milestone(tasks_by_id[tid])
    )
    critical_downstream = sum(1 for tid in visited if tid in critical_task_ids)
    return DownstreamExposure(
        direct_successor_count=len(direct),
        downstream_task_count=len(visited),
        downstream_milestone_count=downstream_milestones,
        critical_downstream_count=critical_downstream,
    )


def build_schedule_drivers(
    task: Task,
    incoming_deps: list[TaskDependency],
    predecessor_names_by_id: dict[str, str],
) -> tuple[ScheduleDriver, ...]:
    """Explanatory summary only -- every incoming dependency is listed as
    a potential driver (this task may have more than one predecessor);
    this deliberately does not attempt to single out which one is
    currently binding, since that would require re-deriving per-edge
    contributions the forward pass does not expose. Does not duplicate
    the full Dependencies section (§8)."""
    drivers: list[ScheduleDriver] = []
    for dep in incoming_deps:
        predecessor_name = predecessor_names_by_id.get(dep.predecessor_task_id, "Unknown task")
        lag = int(dep.lag_days or 0)
        lag_label = "0d" if lag == 0 else (f"+{lag}d" if lag > 0 else f"{abs(lag)}d lead")
        drivers.append(
            ScheduleDriver(
                kind="predecessor",
                label=predecessor_name,
                detail=f"{dep.dependency_type.value} · {lag_label}",
            )
        )
    constraint_type = getattr(task, "constraint_type", None)
    constraint_date = getattr(task, "constraint_date", None)
    if constraint_type and constraint_date:
        drivers.append(
            ScheduleDriver(
                kind="constraint",
                label=str(constraint_type),
                detail=constraint_date.isoformat(),
            )
        )
    actual_start = getattr(task, "actual_start", None)
    if actual_start is not None:
        drivers.append(
            ScheduleDriver(kind="actual_start", label="Actual Start", detail=actual_start.isoformat())
        )
    actual_end = getattr(task, "actual_end", None)
    if actual_end is not None:
        drivers.append(
            ScheduleDriver(kind="actual_finish", label="Actual Finish", detail=actual_end.isoformat())
        )
    return tuple(drivers)


__all__ = [
    "DownstreamExposure",
    "ScheduleDriver",
    "TaskScheduleOverview",
    "build_schedule_drivers",
    "build_successors_by_task_id",
    "compute_downstream_exposure",
    "compute_free_float_days",
]
