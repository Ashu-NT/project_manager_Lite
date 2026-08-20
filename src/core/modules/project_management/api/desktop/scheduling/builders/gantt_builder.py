"""Linear-time assembly of the authoritative disposable Gantt projection."""

from __future__ import annotations

from dataclasses import dataclass
from calendar import monthrange
from datetime import date, timedelta
from typing import Iterable

from src.core.modules.project_management.api.desktop.scheduling.models.gantt import (
    GanttBaselineOverlayDto,
    GanttBaselineTaskSnapshotDto,
    GanttDependencyEdgeDto,
    GanttNonWorkingIntervalDto,
    GanttProjectionDto,
    GanttTaskRowDto,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.tasks.hierarchy import TaskHierarchyNode
from src.core.platform.common.exceptions import BusinessRuleError


def day_ordinal(value: date | None) -> int | None:
    return value.toordinal() if value is not None else None


def build_hierarchy_nodes(tasks: Iterable[object]) -> tuple[TaskHierarchyNode, ...]:
    """Build canonical sibling-order preorder when only task facts are available."""
    task_rows = tuple(tasks)
    task_by_id = {str(task.id): task for task in task_rows}
    if len(task_by_id) != len(task_rows):
        raise BusinessRuleError(
            "The Gantt hierarchy contains duplicate task IDs.",
            code="GANTT_DUPLICATE_TASK_ID",
        )
    children: dict[str | None, list[object]] = {}
    for task in task_rows:
        parent_id = str(task.parent_task_id) if task.parent_task_id else None
        children.setdefault(parent_id, []).append(task)
    for siblings in children.values():
        siblings.sort(key=lambda task: (int(task.sort_order), str(task.wbs_code), str(task.id)))

    result: list[TaskHierarchyNode] = []
    visited: set[str] = set()

    def visit(task: object, depth: int, ancestors: tuple[str, ...]) -> None:
        task_id = str(task.id)
        if task_id in visited:
            raise BusinessRuleError(
                "The Gantt hierarchy contains a cycle.",
                code="GANTT_HIERARCHY_CYCLE",
            )
        visited.add(task_id)
        direct_children = children.get(task_id, [])
        result.append(
            TaskHierarchyNode(
                task=task,
                depth=depth,
                is_summary=bool(direct_children),
                child_count=len(direct_children),
                ancestor_ids=ancestors,
            )
        )
        for child in direct_children:
            visit(child, depth + 1, (*ancestors, task_id))

    for root in children.get(None, []):
        visit(root, 0, ())
    if len(visited) != len(task_rows):
        raise BusinessRuleError(
            "The Gantt hierarchy contains an orphan or cycle.",
            code="GANTT_HIERARCHY_CORRUPT",
        )
    return tuple(result)


@dataclass(slots=True)
class _Rollup:
    start: date | None = None
    finish: date | None = None
    latest_start: date | None = None
    latest_finish: date | None = None
    actual_start: date | None = None
    actual_finish: date | None = None
    weight: int = 0
    weighted_progress: float = 0.0
    leaf_count: int = 0
    unweighted_progress: float = 0.0
    all_done: bool = True
    any_blocked: bool = False
    any_in_progress: bool = False
    is_critical: bool = False
    is_infeasible: bool = False
    total_float_days: int | None = None
    late_by_days: int | None = None
    canonical_count: int = 0

    def include(self, other: "_Rollup") -> None:
        self.start = _min_date(self.start, other.start)
        self.finish = _max_date(self.finish, other.finish)
        self.latest_start = _min_date(self.latest_start, other.latest_start)
        self.latest_finish = _max_date(self.latest_finish, other.latest_finish)
        self.actual_start = _min_date(self.actual_start, other.actual_start)
        self.actual_finish = _max_date(self.actual_finish, other.actual_finish)
        self.weight += other.weight
        self.weighted_progress += other.weighted_progress
        self.leaf_count += other.leaf_count
        self.unweighted_progress += other.unweighted_progress
        self.all_done = self.all_done and other.all_done
        self.any_blocked = self.any_blocked or other.any_blocked
        self.any_in_progress = self.any_in_progress or other.any_in_progress
        self.is_critical = self.is_critical or other.is_critical
        self.is_infeasible = self.is_infeasible or other.is_infeasible
        self.total_float_days = _min_optional_int(
            self.total_float_days, other.total_float_days
        )
        self.late_by_days = _max_optional_int(self.late_by_days, other.late_by_days)
        self.canonical_count += other.canonical_count


def build_gantt_baseline_overlay(
    *,
    tenant_id: str,
    organization_id: str,
    project_id: str,
    baseline_id: str,
    baseline_tasks: Iterable[object],
) -> GanttBaselineOverlayDto:
    """Build one disposable, project-scoped baseline display projection."""
    snapshots = _build_baseline_snapshots(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=project_id,
        baseline_id=baseline_id,
        baseline_tasks=baseline_tasks,
    )
    baseline_days = [
        day
        for snapshot in snapshots
        for day in (
            snapshot.baseline_start_day_ordinal,
            snapshot.baseline_finish_day_ordinal,
        )
        if day is not None
    ]
    return GanttBaselineOverlayDto(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=project_id,
        baseline_id=baseline_id,
        range_start_day_ordinal=min(baseline_days) if baseline_days else None,
        range_finish_day_ordinal=max(baseline_days) if baseline_days else None,
        snapshots=snapshots,
    )


def build_gantt_projection(
    *,
    tenant_id: str,
    organization_id: str,
    project_id: str,
    hierarchy_nodes: Iterable[object],
    schedule_items: Iterable[object],
    dependency_rows: Iterable[object] = (),
    baseline_tasks: Iterable[object] = (),
    selected_baseline_id: str | None = None,
    project_start: date | None = None,
    project_finish: date | None = None,
    work_calendar: object | None = None,
) -> GanttProjectionDto:
    """Merge hierarchy and canonical leaf CPM results in O(N + E + B)."""
    nodes = tuple(hierarchy_nodes)
    schedule_rows = tuple(schedule_items)
    schedule_by_id = {str(item.id): item for item in schedule_rows}
    node_by_id = {str(node.task.id): node for node in nodes}
    if len(node_by_id) != len(nodes):
        raise BusinessRuleError(
            "The Gantt hierarchy contains duplicate task IDs.",
            code="GANTT_DUPLICATE_TASK_ID",
        )
    for node in nodes:
        task = node.task
        if str(task.project_id) != project_id:
            raise BusinessRuleError(
                "The Gantt hierarchy contains a task from another project.",
                code="GANTT_TASK_SCOPE_VIOLATION",
            )
    if len(schedule_by_id) != len(schedule_rows):
        raise BusinessRuleError(
            "The canonical Gantt schedule contains duplicate task IDs.",
            code="GANTT_DUPLICATE_SCHEDULE_TASK_ID",
        )
    if any(str(item.project_id) != project_id for item in schedule_rows):
        raise BusinessRuleError(
            "The canonical Gantt schedule contains a task from another project.",
            code="GANTT_SCHEDULE_SCOPE_VIOLATION",
        )
    leaf_task_ids = {
        str(node.task.id)
        for node in nodes
        if not bool(node.is_summary)
    }
    if set(schedule_by_id) != leaf_task_ids:
        raise BusinessRuleError(
            "The canonical Gantt schedule does not match the complete leaf-task set.",
            code="GANTT_CANONICAL_SCHEDULE_INCOMPLETE",
        )

    children: dict[str, list[str]] = {task_id: [] for task_id in node_by_id}
    for task_id, node in node_by_id.items():
        parent_id = getattr(node.task, "parent_task_id", None)
        if parent_id is not None and str(parent_id) in children:
            children[str(parent_id)].append(task_id)

    rollups: dict[str, _Rollup] = {}
    for node in reversed(nodes):
        task = node.task
        task_id = str(task.id)
        schedule = schedule_by_id.get(task_id)
        if bool(node.is_summary):
            aggregate = _Rollup()
            for child_id in children[task_id]:
                aggregate.include(rollups[child_id])
        else:
            aggregate = _leaf_rollup(task, schedule)
        rollups[task_id] = aggregate

    rows = tuple(
        _build_row(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            node=node,
            schedule=schedule_by_id.get(str(node.task.id)),
            rollup=rollups[str(node.task.id)],
            work_calendar=work_calendar,
        )
        for node in nodes
    )

    project_task_ids = set(node_by_id)
    edges: list[GanttDependencyEdgeDto] = []
    for dependency in dependency_rows:
        predecessor_id = str(dependency.predecessor_task_id)
        successor_id = str(dependency.successor_task_id)
        if predecessor_id not in project_task_ids or successor_id not in project_task_ids:
            raise BusinessRuleError(
                "The Gantt dependency set contains an endpoint outside the project.",
                code="GANTT_EDGE_SCOPE_VIOLATION",
            )
        edges.append(
            GanttDependencyEdgeDto(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                dependency_id=str(dependency.id),
                predecessor_task_id=predecessor_id,
                predecessor_task_name=str(dependency.predecessor_task_name),
                successor_task_id=successor_id,
                successor_task_name=str(dependency.successor_task_name),
                dependency_type=str(dependency.dependency_type),
                dependency_type_label=str(dependency.dependency_type_label),
                lag_days=int(dependency.lag_days or 0),
            )
        )
    edges.sort(
        key=lambda edge: (
            edge.predecessor_task_id,
            edge.successor_task_id,
            edge.dependency_type,
            edge.dependency_id,
        )
    )

    baseline_rows = _build_baseline_snapshots(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=project_id,
        baseline_id=selected_baseline_id or "",
        baseline_tasks=baseline_tasks,
    )
    range_dates = [
        value
        for row in rows
        for value in (
            row.start_date,
            row.finish_date,
            row.actual_start,
            row.actual_finish,
        )
        if value is not None
    ]
    range_dates.extend(
        value for value in (project_start, project_finish) if value is not None
    )
    range_start = min(range_dates) if range_dates else None
    range_finish = max(range_dates) if range_dates else None
    shading_authoritative, non_working_intervals = _build_non_working_intervals(
        work_calendar,
        range_start=_add_months(range_start, -3) if range_start else None,
        range_finish=_add_months(range_finish, 3) if range_finish else None,
    )
    return GanttProjectionDto(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=project_id,
        schedule_authority="canonical",
        selected_baseline_id=selected_baseline_id or None,
        project_start_day_ordinal=day_ordinal(project_start),
        project_finish_day_ordinal=day_ordinal(project_finish),
        range_start_day_ordinal=day_ordinal(range_start),
        range_finish_day_ordinal=day_ordinal(range_finish),
        calendar_shading_authoritative=shading_authoritative,
        non_working_intervals=non_working_intervals,
        rows=rows,
        dependency_edges=tuple(edges),
        baseline_snapshots=baseline_rows,
    )


def _build_baseline_snapshots(
    *,
    tenant_id: str,
    organization_id: str,
    project_id: str,
    baseline_id: str,
    baseline_tasks: Iterable[object],
) -> tuple[GanttBaselineTaskSnapshotDto, ...]:
    sorted_tasks = tuple(
        sorted(
            baseline_tasks,
            key=lambda value: (str(value.task_id), str(value.id)),
        )
    )
    if baseline_id and any(str(item.baseline_id) != baseline_id for item in sorted_tasks):
        raise BusinessRuleError(
            "The Gantt baseline snapshot set contains another baseline.",
            code="GANTT_BASELINE_SCOPE_VIOLATION",
        )
    task_ids = [str(item.task_id) for item in sorted_tasks]
    if len(task_ids) != len(set(task_ids)):
        raise BusinessRuleError(
            "The Gantt baseline snapshot set contains duplicate task IDs.",
            code="GANTT_DUPLICATE_BASELINE_TASK_ID",
        )
    return tuple(
        GanttBaselineTaskSnapshotDto(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            baseline_id=str(item.baseline_id),
            task_id=str(item.task_id),
            baseline_start=item.baseline_start,
            baseline_finish=item.baseline_finish,
            baseline_duration_days=int(item.baseline_duration_days or 0),
            baseline_is_milestone=bool(item.baseline_is_milestone),
            baseline_start_day_ordinal=day_ordinal(item.baseline_start),
            baseline_finish_day_ordinal=day_ordinal(item.baseline_finish),
        )
        for item in sorted_tasks
    )


def _leaf_rollup(task: object, schedule: object | None) -> _Rollup:
    status = _enum_value(getattr(task, "status", "todo"))
    duration = max(int(getattr(task, "duration_days", 0) or 0), 0)
    progress = float(getattr(task, "percent_complete", 0.0) or 0.0)
    return _Rollup(
        start=getattr(schedule, "start_date", None) if schedule else getattr(task, "start_date", None),
        finish=getattr(schedule, "finish_date", None) if schedule else getattr(task, "end_date", None),
        latest_start=getattr(schedule, "latest_start", None) if schedule else None,
        latest_finish=getattr(schedule, "latest_finish", None) if schedule else None,
        actual_start=getattr(task, "actual_start", None),
        actual_finish=getattr(task, "actual_end", None),
        weight=duration,
        weighted_progress=progress * duration,
        leaf_count=1,
        unweighted_progress=progress,
        all_done=status == TaskStatus.DONE.value,
        any_blocked=status == TaskStatus.BLOCKED.value,
        any_in_progress=(
            status == TaskStatus.IN_PROGRESS.value or progress > 0
        ),
        is_critical=bool(getattr(schedule, "is_critical", False)),
        is_infeasible=bool(getattr(schedule, "is_infeasible", False)),
        total_float_days=getattr(schedule, "total_float_days", None),
        late_by_days=getattr(schedule, "late_by_days", None),
        canonical_count=1 if schedule is not None else 0,
    )


def _build_row(
    *,
    tenant_id: str,
    organization_id: str,
    project_id: str,
    node: object,
    schedule: object | None,
    rollup: _Rollup,
    work_calendar: object | None,
) -> GanttTaskRowDto:
    task = node.task
    is_summary = bool(node.is_summary)
    if is_summary:
        status = _summary_status(rollup)
        status_label = status.replace("_", " ").title()
        progress = _rollup_progress(rollup)
        duration = _summary_duration(rollup, work_calendar)
        remaining = max(0, int(round(duration * (1.0 - progress / 100.0))))
        start = rollup.start
        finish = rollup.finish
        latest_start = rollup.latest_start
        latest_finish = rollup.latest_finish
        actual_start = rollup.actual_start
        actual_finish = rollup.actual_finish
        total_float = rollup.total_float_days
        late_by_days = rollup.late_by_days
        canonical = rollup.leaf_count > 0 and rollup.canonical_count == rollup.leaf_count
    else:
        status = _enum_value(getattr(task, "status", "todo"))
        status_label = str(
            getattr(schedule, "status_label", "")
            or status.replace("_", " ").title()
        )
        progress = float(getattr(task, "percent_complete", 0.0) or 0.0)
        duration = getattr(task, "duration_days", None)
        remaining = getattr(task, "remaining_duration_days", None)
        start = rollup.start
        finish = rollup.finish
        latest_start = rollup.latest_start
        latest_finish = rollup.latest_finish
        actual_start = rollup.actual_start
        actual_finish = rollup.actual_finish
        total_float = rollup.total_float_days
        late_by_days = rollup.late_by_days
        canonical = schedule is not None

    constraint_type = "" if is_summary else str(getattr(schedule, "constraint_type", "") or "")
    constraint_label = "" if is_summary else str(
        getattr(schedule, "constraint_type_label", "") or ""
    )
    constraint_date = None if is_summary else getattr(task, "constraint_date", None)
    return GanttTaskRowDto(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=project_id,
        task_id=str(task.id),
        code=str(getattr(task, "code", "") or ""),
        name=str(task.name),
        description=str(getattr(task, "description", "") or ""),
        parent_task_id=(str(task.parent_task_id) if task.parent_task_id else None),
        wbs_code=str(getattr(task, "wbs_code", "") or ""),
        sort_order=int(getattr(task, "sort_order", 0) or 0),
        depth=int(node.depth),
        is_summary=is_summary,
        child_count=int(node.child_count),
        ancestor_ids=tuple(str(value) for value in node.ancestor_ids),
        start_date=start,
        finish_date=finish,
        start_day_ordinal=day_ordinal(start),
        finish_day_ordinal=day_ordinal(finish),
        latest_start=latest_start,
        latest_finish=latest_finish,
        duration_days=duration,
        remaining_duration_days=remaining,
        status=status,
        status_label=status_label,
        percent_complete=round(progress, 4),
        is_milestone=(False if is_summary else bool(getattr(task, "is_milestone", False))),
        is_critical=rollup.is_critical,
        is_infeasible=rollup.is_infeasible,
        total_float_days=total_float,
        has_canonical_schedule=canonical,
        constraint_type=constraint_type,
        constraint_type_label=constraint_label,
        constraint_date=constraint_date,
        actual_start=actual_start,
        actual_finish=actual_finish,
        actual_start_day_ordinal=day_ordinal(actual_start),
        actual_finish_day_ordinal=day_ordinal(actual_finish),
        deadline=(None if is_summary else getattr(task, "deadline", None)),
        late_by_days=late_by_days,
        priority=(None if is_summary else getattr(task, "priority", None)),
    )


def _summary_status(rollup: _Rollup) -> str:
    if rollup.leaf_count and rollup.all_done:
        return TaskStatus.DONE.value
    if rollup.any_blocked:
        return TaskStatus.BLOCKED.value
    if rollup.any_in_progress:
        return TaskStatus.IN_PROGRESS.value
    return TaskStatus.TODO.value


def _rollup_progress(rollup: _Rollup) -> float:
    if rollup.weight:
        return rollup.weighted_progress / rollup.weight
    if rollup.leaf_count:
        return rollup.unweighted_progress / rollup.leaf_count
    return 0.0


def _summary_duration(rollup: _Rollup, work_calendar: object | None) -> int:
    if rollup.start is not None and rollup.finish is not None:
        calculate = getattr(work_calendar, "working_days_between", None)
        if callable(calculate):
            return max(0, int(calculate(rollup.start, rollup.finish)))
    return rollup.weight


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value) or "")


def _min_date(left: date | None, right: date | None) -> date | None:
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


def _max_date(left: date | None, right: date | None) -> date | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)


def _min_optional_int(left: int | None, right: int | None) -> int | None:
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


def _max_optional_int(left: int | None, right: int | None) -> int | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _build_non_working_intervals(
    work_calendar: object | None,
    *,
    range_start: date | None,
    range_finish: date | None,
) -> tuple[bool, tuple[GanttNonWorkingIntervalDto, ...]]:
    if work_calendar is None or range_start is None or range_finish is None:
        return False, ()
    working_dates_between = getattr(work_calendar, "working_day_dates_between", None)
    is_working_day = getattr(work_calendar, "is_working_day", None)
    if callable(working_dates_between):
        working_dates = set(working_dates_between(range_start, range_finish))

        def predicate(value: date) -> bool:
            return value in working_dates

    elif callable(is_working_day):
        predicate = is_working_day
    else:
        return False, ()

    intervals: list[GanttNonWorkingIntervalDto] = []
    interval_start: date | None = None
    cursor = range_start
    while cursor <= range_finish:
        if not predicate(cursor):
            interval_start = interval_start or cursor
        elif interval_start is not None:
            intervals.append(
                GanttNonWorkingIntervalDto(
                    start_day_ordinal=interval_start.toordinal(),
                    finish_day_ordinal=(cursor - timedelta(days=1)).toordinal(),
                )
            )
            interval_start = None
        cursor += timedelta(days=1)
    if interval_start is not None:
        intervals.append(
            GanttNonWorkingIntervalDto(
                start_day_ordinal=interval_start.toordinal(),
                finish_day_ordinal=range_finish.toordinal(),
            )
        )
    return True, tuple(intervals)


__all__ = ["build_gantt_projection", "build_hierarchy_nodes", "day_ordinal"]
