from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Callable

from core.models import Task, TaskAssignment, TaskDependency
from core.services.scheduling.leveling_models import ResourceConflict, ResourceConflictEntry
from core.services.work_calendar.engine import WorkCalendarEngine


def build_successors_map(deps: list[TaskDependency]) -> dict[str, set[str]]:
    successors: dict[str, set[str]] = defaultdict(set)
    for dep in deps:
        successors[dep.predecessor_task_id].add(dep.successor_task_id)
    return successors


def build_resource_conflicts(
    tasks_by_id: dict[str, Task],
    assignments: list[TaskAssignment],
    calendar: WorkCalendarEngine,
    resource_name_by_id: dict[str, str],
    threshold_percent: float = 100.0,
) -> list[ResourceConflict]:
    bucket: dict[tuple[str, date], list[tuple[Task, float]]] = defaultdict(list)
    for assignment in assignments:
        task = tasks_by_id.get(assignment.task_id)
        if task is None or task.start_date is None or task.end_date is None:
            continue
        alloc = float(assignment.allocation_percent or 0.0)
        if alloc <= 0:
            continue
        for day in _iter_workdays(task.start_date, task.end_date, calendar):
            bucket[(assignment.resource_id, day)].append((task, alloc))

    conflicts: list[ResourceConflict] = []
    for (resource_id, day), values in bucket.items():
        total = sum(alloc for _, alloc in values)
        if total <= threshold_percent + 1e-9:
            continue
        task_alloc: dict[str, float] = defaultdict(float)
        task_name: dict[str, str] = {}
        for task, alloc in values:
            task_alloc[task.id] += alloc
            task_name[task.id] = task.name
        entries = [
            ResourceConflictEntry(
                task_id=task_id,
                task_name=task_name.get(task_id, task_id),
                allocation_percent=alloc,
            )
            for task_id, alloc in task_alloc.items()
        ]
        entries.sort(key=lambda e: (-e.allocation_percent, e.task_name.lower()))
        conflicts.append(
            ResourceConflict(
                resource_id=resource_id,
                resource_name=resource_name_by_id.get(resource_id, resource_id),
                conflict_date=day,
                total_allocation_percent=total,
                entries=entries,
            )
        )

    conflicts.sort(
        key=lambda c: (
            c.conflict_date,
            c.resource_name.lower(),
            -c.total_allocation_percent,
        )
    )
    return conflicts


def choose_auto_level_task(
    conflict: ResourceConflict,
    tasks_by_id: dict[str, Task],
    successors_by_task_id: dict[str, set[str]],
    priority_value: Callable[[Task], int],
) -> str | None:
    candidates: list[tuple[float, int, int, str]] = []
    for entry in conflict.entries:
        task = tasks_by_id.get(entry.task_id)
        if task is None or task.start_date is None:
            continue
        if successors_by_task_id.get(task.id):
            continue
        if getattr(task, "actual_start", None) is not None or getattr(task, "actual_end", None) is not None:
            continue
        if float(getattr(task, "percent_complete", 0.0) or 0.0) > 0.0:
            continue
        candidates.append(
            (
                float(getattr(task, "percent_complete", 0.0) or 0.0),
                -priority_value(task),
                -task.start_date.toordinal(),
                task.id,
            )
        )
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][3]


def _iter_workdays(start: date, end: date, calendar: WorkCalendarEngine):
    cur = start
    while cur <= end:
        if calendar.is_working_day(cur):
            yield cur
        cur += timedelta(days=1)


__all__ = [
    "build_successors_map",
    "build_resource_conflicts",
    "choose_auto_level_task",
]
