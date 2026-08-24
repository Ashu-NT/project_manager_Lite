from __future__ import annotations

from datetime import date
from time import perf_counter
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.gantt_builder import (
    build_gantt_projection,
)
from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.core.modules.project_management.domain.scheduling.baseline import BaselineTask
from src.core.modules.project_management.domain.tasks.hierarchy import TaskHierarchyNode
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.ui_qml.modules.project_management.controllers.scheduling.gantt_list_model import (
    GanttListModel,
)
from src.ui_qml.modules.project_management.controllers.scheduling.scheduling_workspace_controller import (
    ProjectManagementSchedulingWorkspaceController,
)


def test_projection_preserves_authoritative_identity_hierarchy_milestones_and_dates() -> None:
    summary = _task("summary", code="SUM", wbs="1", sort_order=0)
    same_day = _task(
        "same-day",
        code="TASK-001",
        wbs="1.1",
        parent_id=summary.id,
        sort_order=0,
        is_milestone=False,
    )
    milestone = _task(
        "milestone",
        code="MILE-001",
        wbs="1.2",
        parent_id=summary.id,
        sort_order=1,
        is_milestone=True,
    )
    nodes = (
        _node(summary, depth=0, is_summary=True, child_count=2),
        _node(same_day, depth=1, ancestors=(summary.id,)),
        _node(milestone, depth=1, ancestors=(summary.id,)),
    )
    schedules = (
        _schedule(same_day, start=date(2026, 6, 1), finish=date(2026, 6, 1)),
        _schedule(milestone, start=date(2026, 6, 3), finish=date(2026, 6, 3)),
    )
    edge_rows = tuple(
        _edge(index, same_day.id, milestone.id, relation, lag)
        for index, (relation, lag) in enumerate(
            (("FS", -2), ("SS", 0), ("FF", 3), ("SF", 1)), start=1
        )
    )
    baseline = BaselineTask.create(
        baseline_id="baseline-1",
        task_id=milestone.id,
        task_name=milestone.name,
        baseline_start=date(2026, 5, 30),
        baseline_finish=date(2026, 5, 30),
        baseline_duration_days=0,
        baseline_planned_cost=0,
        baseline_is_milestone=True,
    )

    projection = build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=nodes,
        schedule_items=schedules,
        dependency_rows=edge_rows,
        baseline_tasks=(baseline,),
        selected_baseline_id="baseline-1",
    )

    assert [row.task_id for row in projection.rows] == [
        summary.id,
        same_day.id,
        milestone.id,
    ]
    assert projection.rows[0].is_summary is True
    assert projection.rows[0].child_count == 2
    assert projection.rows[0].start_date == date(2026, 6, 1)
    assert projection.rows[0].finish_date == date(2026, 6, 3)
    assert projection.rows[1].code == "TASK-001"
    assert projection.rows[1].is_milestone is False
    assert projection.rows[2].code == "MILE-001"
    assert projection.rows[2].is_milestone is True
    assert projection.rows[2].start_day_ordinal == date(2026, 6, 3).toordinal()
    assert [edge.dependency_type for edge in projection.dependency_edges] == [
        "FF",
        "FS",
        "SF",
        "SS",
    ]
    assert sorted(edge.lag_days for edge in projection.dependency_edges) == [-2, 0, 1, 3]
    assert projection.baseline_snapshots[0].baseline_is_milestone is True
    assert projection.baseline_snapshots[0].baseline_start_day_ordinal == date(
        2026, 5, 30
    ).toordinal()


def test_indexed_model_applies_hierarchy_and_flat_view_semantics() -> None:
    projection = _projection(8, with_edges=True, with_baseline=True)
    model = GanttListModel()
    model.set_projection(projection)

    assert model.scheduleAuthority == "canonical"
    assert model.row_for_task("task-7").task_id == "task-7"
    assert model.incident_edge_ids("task-7") == ("edge-7",)
    assert model.baseline_for_task("task-7").task_id == "task-7"

    model.apply_view(
        search_text="Task 7",
        status_filter="all",
        critical_only=False,
        delayed_only=False,
        sort_key="schedule",
        sort_descending=False,
    )
    assert model.hierarchyMode is True
    assert [row.task_id for row in model.effective_rows] == ["task-7"]

    model.apply_view(
        search_text="",
        status_filter="all",
        critical_only=False,
        delayed_only=False,
        sort_key="taskName",
        sort_descending=True,
    )
    assert model.hierarchyMode is False
    assert model.effective_rows[0].name == "Task 7"


def test_flat_sort_keeps_missing_values_last_in_both_directions() -> None:
    dated = _task("dated", code="T-1", wbs="1")
    unscheduled = _task("unscheduled", code="T-2", wbs="2")
    projection = build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=(_node(dated), _node(unscheduled)),
        schedule_items=(
            _schedule(dated, start=date(2026, 1, 1), finish=date(2026, 1, 2)),
            _schedule(unscheduled, start=None, finish=None),
        ),
    )
    model = GanttListModel()
    model.set_projection(projection)

    for descending in (False, True):
        model.apply_view(
            search_text="",
            status_filter="all",
            critical_only=False,
            delayed_only=False,
            sort_key="start",
            sort_descending=descending,
        )
        assert [row.task_id for row in model.effective_rows] == [
            "dated",
            "unscheduled",
        ]


def test_controller_selection_and_local_view_operations_do_not_refresh() -> None:
    controller = ProjectManagementSchedulingWorkspaceController()
    controller._gantt_model.set_projection(_projection(3))
    refresh_calls = 0

    def fail_refresh() -> None:
        nonlocal refresh_calls
        refresh_calls += 1
        raise AssertionError("Local Gantt action must not rebuild the workspace.")

    controller.refresh = fail_refresh
    observed: list[tuple[str, str]] = []
    controller.selectedActivityIdChanged.connect(
        lambda: observed.append(
            (controller.selectedActivityId, controller.selectedActivity["taskId"])
        )
    )

    controller.selectActivity("task-1")

    assert controller.selectedActivityId == "task-1"
    assert controller.selectedActivity["taskId"] == "task-1"
    assert observed == [("task-1", "task-1")]

    controller.setSearchText("Task 2")
    assert controller.selectedActivityId == ""
    assert controller.selectedActivity["taskId"] == ""
    controller.setActivitySort("taskName", 1)
    controller.setShowCriticalOnly(True)
    assert refresh_calls == 0


def test_desktop_api_requires_canonical_engine_and_rejects_scope_mismatch() -> None:
    task = _task("task-1", code="TASK-001", wbs="1")
    node = _node(task)
    engine = _CountingEngine(task)
    task_service = SimpleNamespace(
        list_task_hierarchy=lambda _project_id: [node],
        list_tasks_for_project=lambda _project_id: [task],
        list_dependencies_for_project=lambda _project_id: [],
    )
    project = SimpleNamespace(
        id="project-1",
        name="Project",
        tenant_id="tenant-1",
        organization_id="org-1",
    )
    api = ProjectManagementSchedulingDesktopApi(
        project_service=SimpleNamespace(get_project=lambda _project_id: project),
        task_service=task_service,
        scheduling_engine=engine,
        tenant_context_service=_ScopeContext("tenant-1", "org-1"),
    )

    projection = api.build_gantt_projection("project-1")

    assert projection.tenant_id == "tenant-1"
    assert projection.organization_id == "org-1"
    assert projection.project_id == "project-1"
    assert projection.schedule_authority == "canonical"
    assert engine.calls == 1

    wrong_org_api = ProjectManagementSchedulingDesktopApi(
        project_service=SimpleNamespace(get_project=lambda _project_id: project),
        task_service=task_service,
        scheduling_engine=engine,
        tenant_context_service=_ScopeContext("tenant-1", "org-2"),
    )
    with pytest.raises(NotFoundError):
        wrong_org_api.build_gantt_projection("project-1")
    assert engine.calls == 1

    degraded_api = ProjectManagementSchedulingDesktopApi(
        project_service=SimpleNamespace(get_project=lambda _project_id: project),
        task_service=task_service,
        tenant_context_service=_ScopeContext("tenant-1", "org-1"),
    )
    with pytest.raises(RuntimeError, match="not connected"):
        degraded_api.build_gantt_projection("project-1")


def test_projection_rejects_cross_project_edges_and_mixed_baselines() -> None:
    task = _task("task-1", code="TASK-001", wbs="1")
    schedule = _schedule(task, start=date(2026, 1, 1), finish=date(2026, 1, 2))
    with pytest.raises(BusinessRuleError) as edge_error:
        build_gantt_projection(
            tenant_id="tenant-1",
            organization_id="org-1",
            project_id="project-1",
            hierarchy_nodes=(_node(task),),
            schedule_items=(schedule,),
            dependency_rows=(_edge(1, task.id, "foreign-task", "FS", 0),),
        )
    assert edge_error.value.code == "GANTT_EDGE_SCOPE_VIOLATION"

    foreign_baseline = BaselineTask.create(
        baseline_id="baseline-2",
        task_id=task.id,
        task_name=task.name,
        baseline_start=None,
        baseline_finish=None,
        baseline_duration_days=0,
        baseline_planned_cost=0,
    )
    with pytest.raises(BusinessRuleError) as baseline_error:
        build_gantt_projection(
            tenant_id="tenant-1",
            organization_id="org-1",
            project_id="project-1",
            hierarchy_nodes=(_node(task),),
            schedule_items=(schedule,),
            baseline_tasks=(foreign_baseline,),
            selected_baseline_id="baseline-1",
        )
    assert baseline_error.value.code == "GANTT_BASELINE_SCOPE_VIOLATION"


def test_projection_rejects_incomplete_and_cross_scope_canonical_schedule() -> None:
    first = _task("task-1", code="TASK-001", wbs="1")
    second = _task("task-2", code="TASK-002", wbs="2")
    nodes = (_node(first), _node(second))

    with pytest.raises(BusinessRuleError) as incomplete_error:
        build_gantt_projection(
            tenant_id="tenant-1",
            organization_id="org-1",
            project_id="project-1",
            hierarchy_nodes=nodes,
            schedule_items=(
                _schedule(first, start=date(2026, 1, 1), finish=date(2026, 1, 2)),
            ),
        )
    assert incomplete_error.value.code == "GANTT_CANONICAL_SCHEDULE_INCOMPLETE"

    foreign_schedule = _schedule(
        first, start=date(2026, 1, 1), finish=date(2026, 1, 2)
    )
    foreign_schedule.project_id = "project-2"
    with pytest.raises(BusinessRuleError) as scope_error:
        build_gantt_projection(
            tenant_id="tenant-1",
            organization_id="org-1",
            project_id="project-1",
            hierarchy_nodes=(_node(first),),
            schedule_items=(foreign_schedule,),
        )
    assert scope_error.value.code == "GANTT_SCHEDULE_SCOPE_VIOLATION"


@pytest.mark.parametrize("row_count", [100, 1_000, 5_000])
def test_projection_and_index_construction_scale_linearly(row_count: int) -> None:
    nodes = []
    schedules = []
    dependencies = []
    baselines = []
    for index in range(row_count):
        task = _task(f"task-{index}", code=f"T-{index:05d}", wbs=str(index + 1))
        nodes.append(_node(task))
        schedules.append(
            _schedule(task, start=date(2026, 1, 1), finish=date(2026, 1, 2))
        )
        baselines.append(
            BaselineTask.create(
                baseline_id="baseline-1",
                task_id=task.id,
                task_name=task.name,
                baseline_start=date(2025, 12, 31),
                baseline_finish=date(2026, 1, 1),
                baseline_duration_days=2,
                baseline_planned_cost=0,
            )
        )
        if index:
            dependencies.append(
                _edge(index, f"task-{index - 1}", task.id, "FS", 0)
            )

    started = perf_counter()
    projection = build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=nodes,
        schedule_items=schedules,
        dependency_rows=dependencies,
        baseline_tasks=baselines,
        selected_baseline_id="baseline-1",
    )
    projection_seconds = perf_counter() - started
    model = GanttListModel()
    index_started = perf_counter()
    model.set_projection(projection)
    index_seconds = perf_counter() - index_started

    assert len(projection.rows) == row_count
    assert model.row_for_task(f"task-{row_count - 1}") is not None
    assert projection_seconds < 3.0
    assert index_seconds < 3.0


class _ScopeContext:
    def __init__(self, tenant_id: str, organization_id: str) -> None:
        self._scope = SimpleNamespace(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )

    def require_active_scope_ids(self, **_kwargs):
        return self._scope


class _CountingEngine:
    def __init__(self, task: SimpleNamespace) -> None:
        self.task = task
        self.calls = 0

    def recalculate_project_schedule(self, _project_id: str, *, persist: bool = False):
        self.calls += 1
        return {
            self.task.id: SimpleNamespace(
                task=self.task,
                earliest_start=date(2026, 1, 1),
                earliest_finish=date(2026, 1, 2),
                latest_start=date(2026, 1, 1),
                latest_finish=date(2026, 1, 2),
                total_float_days=0,
                is_critical=True,
                is_infeasible=False,
                deadline=None,
                late_by_days=0,
            )
        }


def _task(
    task_id: str,
    *,
    code: str = "",
    wbs: str = "",
    parent_id: str | None = None,
    sort_order: int = 0,
    is_milestone: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=task_id,
        project_id="project-1",
        code=code,
        name=task_id.replace("-", " ").title(),
        description=f"Description {task_id}",
        parent_task_id=parent_id,
        wbs_code=wbs,
        sort_order=sort_order,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        duration_days=2,
        remaining_duration_days=2,
        status=TaskStatus.TODO,
        percent_complete=0.0,
        actual_start=None,
        actual_end=None,
        deadline=None,
        constraint_type=None,
        constraint_date=None,
        is_milestone=is_milestone,
        priority=0,
    )


def _node(
    task: SimpleNamespace,
    *,
    depth: int = 0,
    is_summary: bool = False,
    child_count: int = 0,
    ancestors: tuple[str, ...] = (),
) -> TaskHierarchyNode:
    return TaskHierarchyNode(
        task=task,
        depth=depth,
        is_summary=is_summary,
        child_count=child_count,
        ancestor_ids=ancestors,
    )


def _schedule(
    task: SimpleNamespace,
    *,
    start: date | None,
    finish: date | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=task.id,
        project_id=task.project_id,
        code=task.code,
        name=task.name,
        parent_task_id=task.parent_task_id,
        wbs_code=task.wbs_code,
        sort_order=task.sort_order,
        is_milestone=task.is_milestone,
        description=task.description,
        status=task.status.value,
        status_label=task.status.value.title(),
        start_date=start,
        finish_date=finish,
        latest_start=start,
        latest_finish=finish,
        duration_days=task.duration_days,
        remaining_duration_days=task.remaining_duration_days,
        total_float_days=0,
        is_critical=True,
        is_infeasible=False,
        deadline=task.deadline,
        late_by_days=0,
        percent_complete=task.percent_complete,
        actual_start=task.actual_start,
        actual_end=task.actual_end,
        priority=task.priority,
        constraint_type="",
        constraint_type_label="As Soon As Possible",
        constraint_date=None,
    )


def _edge(
    index: int,
    predecessor_id: str,
    successor_id: str,
    relation: str,
    lag: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"edge-{index}",
        predecessor_task_id=predecessor_id,
        predecessor_task_name=predecessor_id,
        successor_task_id=successor_id,
        successor_task_name=successor_id,
        dependency_type=relation,
        dependency_type_label=relation,
        lag_days=lag,
    )


def _projection(
    row_count: int,
    *,
    with_edges: bool = False,
    with_baseline: bool = False,
):
    tasks = [
        _task(f"task-{index}", code=f"T-{index}", wbs=str(index + 1))
        for index in range(row_count)
    ]
    return build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=tuple(_node(task) for task in tasks),
        schedule_items=tuple(
            _schedule(task, start=date(2026, 1, 1), finish=date(2026, 1, 2))
            for task in tasks
        ),
        dependency_rows=(
            tuple(_edge(index, tasks[index - 1].id, tasks[index].id, "FS", 0) for index in range(1, row_count))
            if with_edges
            else ()
        ),
        baseline_tasks=(
            tuple(
                BaselineTask.create(
                    baseline_id="baseline-1",
                    task_id=task.id,
                    task_name=task.name,
                    baseline_start=date(2025, 12, 31),
                    baseline_finish=date(2026, 1, 1),
                    baseline_duration_days=2,
                    baseline_planned_cost=0,
                )
                for task in tasks
            )
            if with_baseline
            else ()
        ),
        selected_baseline_id="baseline-1" if with_baseline else None,
    )
