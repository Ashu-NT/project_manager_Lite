from __future__ import annotations

import gc
import os
from datetime import date, timedelta
from pathlib import Path
from time import perf_counter
import tracemalloc
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

import src.ui_qml.modules.project_management.controllers.scheduling.gantt_baseline_actions as baseline_actions
import src.ui_qml.modules.project_management.controllers.scheduling.gantt_view_state as gantt_view_state
from src.core.modules.project_management.api.desktop.scheduling.builders.gantt_builder import (
    build_gantt_projection,
)
from src.core.modules.project_management.domain.scheduling.baseline import BaselineTask
from src.tests.path_rewrites import REPO_ROOT
from src.tests.project_management.test_r4_5b_gantt_read_contract import _projection
from src.tests.project_management.test_r4_5c_gantt_viewport import (
    _projection_from_hierarchy,
)
from src.tests.project_management.test_r4_5b_gantt_read_contract import (
    _edge,
    _node,
    _schedule,
    _task,
)
from src.ui_qml.modules.project_management.controllers.scheduling.gantt_list_model import (
    GanttListModel,
)
from src.ui_qml.modules.project_management.controllers.scheduling.gantt_time_axis_controller import (
    GanttTimeAxisController,
)
from src.ui_qml.modules.project_management.controllers.scheduling.scheduling_workspace_controller import (
    ProjectManagementSchedulingWorkspaceController,
)
from src.ui_qml.shell.qml_engine import create_qml_engine


SCHEDULING_ROOT = (
    REPO_ROOT
    / "src"
    / "ui_qml"
    / "modules"
    / "project_management"
    / "qml"
    / "workspaces"
    / "scheduling"
)
GANTT_ROOT = SCHEDULING_ROOT / "components" / "gantt"


def _application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    return existing or QGuiApplication(["r4-5g-gantt-test"])


def _process_events(application: QGuiApplication, passes: int = 8) -> None:
    for _ in range(passes):
        application.processEvents()


def _create_view(
    source: Path,
    *,
    width: int,
    height: int,
    initial_properties: dict[str, object] | None = None,
):
    application = _application()
    engine = create_qml_engine()
    view = QQuickView(engine, None)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    if initial_properties:
        view.setInitialProperties(initial_properties)
    view.setSource(QUrl.fromLocalFile(str(source)))
    assert view.status() == QQuickView.Ready, "\n".join(
        error.toString() for error in view.errors()
    )
    view.resize(width, height)
    view.show()
    _process_events(application)
    QTest.qWait(30)
    root = view.rootObject()
    assert root is not None
    return application, engine, view, root


def _combined_projection(
    row_count: int,
    *,
    project_id: str = "project-a",
    prefix: str = "a",
):
    assert row_count >= 50 and row_count % 50 == 0
    hierarchy_nodes = []
    schedule_items = []
    baseline_tasks = []
    leaf_tasks = []
    base_date = date(2026, 1, 1)

    for group_index in range(row_count // 50):
        summary = _task(
            f"{prefix}-summary-{group_index}",
            code=f"{prefix.upper()}-S-{group_index}",
            wbs=str(group_index + 1),
            sort_order=group_index,
        )
        summary.project_id = project_id
        hierarchy_nodes.append(_node(summary, is_summary=True, child_count=49))

        for child_index in range(49):
            leaf_index = len(leaf_tasks)
            milestone = leaf_index % 37 == 0
            task = _task(
                f"{prefix}-task-{leaf_index}",
                code=f"{prefix.upper()}-T-{leaf_index}",
                wbs=f"{group_index + 1}.{child_index + 1}",
                parent_id=summary.id,
                sort_order=child_index,
                is_milestone=milestone,
            )
            task.project_id = project_id
            if milestone:
                task.duration_days = 0
                task.remaining_duration_days = 0
            start = base_date + timedelta(days=leaf_index % 365)
            finish = start if milestone else start + timedelta(days=2)
            schedule = _schedule(task, start=start, finish=finish)
            schedule.is_critical = leaf_index % 3 == 0
            schedule.is_infeasible = leaf_index % 97 == 0
            hierarchy_nodes.append(_node(task, depth=1, ancestors=(summary.id,)))
            schedule_items.append(schedule)
            baseline_tasks.append(
                BaselineTask.create(
                    baseline_id=f"{prefix}-baseline",
                    task_id=task.id,
                    task_name=task.name,
                    baseline_start=start - timedelta(days=7),
                    baseline_finish=finish - timedelta(days=7),
                    baseline_duration_days=task.duration_days,
                    baseline_planned_cost=0,
                    baseline_is_milestone=milestone,
                )
            )
            leaf_tasks.append(task)

    relationships = ("FS", "SS", "FF", "SF")
    dependency_rows = []
    for index in range(1, len(leaf_tasks)):
        edge = _edge(
            index,
            leaf_tasks[index - 1].id,
            leaf_tasks[index].id,
            relationships[index % len(relationships)],
            (index % 5) - 2,
        )
        edge.id = f"{prefix}-edge-{index}"
        dependency_rows.append(edge)

    return build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id=project_id,
        hierarchy_nodes=tuple(hierarchy_nodes),
        schedule_items=tuple(schedule_items),
        dependency_rows=tuple(dependency_rows),
        baseline_tasks=tuple(baseline_tasks),
        selected_baseline_id=f"{prefix}-baseline",
    )


@pytest.mark.parametrize(
    ("width", "height", "inline_inspector", "overflow_visible", "effective_mode"),
    (
        (1024, 640, False, True, "grid"),
        (1280, 720, False, True, "split"),
        (1366, 768, True, False, "split"),
        (1440, 900, True, False, "split"),
        (1920, 1080, True, False, "split"),
    ),
)
def test_runtime_responsive_matrix_preserves_usable_gantt_geometry(
    width: int,
    height: int,
    inline_inspector: bool,
    overflow_visible: bool,
    effective_mode: str,
) -> None:
    application, _engine, view, panel = _create_view(
        SCHEDULING_ROOT / "panels" / "SchedulingGanttPanel.qml",
        width=width,
        height=height,
        initial_properties={
            "ganttViewMode": "split",
            "selectedActivityModel": {
                "id": "task-1",
                "title": "Task 1",
                "statusLabel": "On track",
                "fields": [],
            },
        },
    )
    surface = panel.findChild(QObject, "schedulingGanttSurface")
    toolbar = panel.findChild(QObject, "ganttPrimaryToolbar")
    overflow = panel.findChild(QObject, "ganttOptionsOverflowButton")
    inline = panel.findChild(QObject, "ganttInlineInspector")
    slide_over = panel.findChild(QObject, "ganttSlideOverInspector")
    assert all(item is not None for item in (surface, toolbar, overflow, inline, slide_over))

    assert bool(panel.property("inspectorInline")) is inline_inspector
    assert bool(overflow.property("visible")) is overflow_visible
    assert bool(inline.property("active")) is inline_inspector
    assert bool(slide_over.property("open")) is (not inline_inspector)
    assert str(surface.property("requestedViewMode")) == "split"
    assert str(surface.property("effectiveViewMode")) == effective_mode
    assert float(surface.property("height")) >= 240
    assert float(toolbar.property("width")) <= float(panel.property("width"))

    if effective_mode == "split":
        assert float(surface.property("gridWidth")) >= 420
        assert float(surface.property("timelineWidth")) >= 360
    else:
        assert float(surface.property("gridWidth")) == pytest.approx(
            float(surface.property("width"))
        )
        assert panel.setProperty("ganttViewMode", "timeline")
        _process_events(application)
        assert str(surface.property("effectiveViewMode")) == "timeline"
        assert float(surface.property("timelineWidth")) == pytest.approx(
            float(surface.property("width"))
        )

    view.close()
    panel.deleteLater()
    _process_events(application)


def test_requested_split_survives_compact_fallback_and_ratio_is_clamped() -> None:
    application, _engine, view, surface = _create_view(
        GANTT_ROOT / "SchedulingGanttSurface.qml",
        width=1024,
        height=640,
        initial_properties={"requestedViewMode": "split", "requestedSplitRatio": 0.9},
    )
    assert str(surface.property("requestedViewMode")) == "split"
    assert str(surface.property("effectiveViewMode")) == "grid"

    view.resize(1280, 720)
    _process_events(application)
    assert str(surface.property("requestedViewMode")) == "split"
    assert str(surface.property("effectiveViewMode")) == "split"
    assert float(surface.property("gridWidth")) >= 420
    assert float(surface.property("timelineWidth")) >= 360
    assert float(surface.property("effectiveSplitRatio")) <= 0.72

    view.close()
    surface.deleteLater()
    _process_events(application)


def test_resize_thresholds_preserve_requested_mode_selection_and_view_state() -> None:
    application, _engine, view, panel = _create_view(
        SCHEDULING_ROOT / "panels" / "SchedulingGanttPanel.qml",
        width=1440,
        height=900,
        initial_properties={
            "ganttViewMode": "split",
            "selectedActivityModel": {
                "id": "task-1",
                "title": "Task 1",
                "statusLabel": "On track",
                "fields": [],
            },
        },
    )
    surface = panel.findChild(QObject, "schedulingGanttSurface")
    overflow = panel.findChild(QObject, "ganttOptionsOverflowButton")
    assert surface is not None and overflow is not None
    assert surface.setProperty("selectedActivityId", "task-1")

    for width in (1020, 1024, 1028, 1276, 1280, 1284, 1316, 1320, 1324, 1356, 1360, 1364, 1920):
        view.resize(width, 720)
        _process_events(application, passes=3)
        expected_mode = str(surface.property("effectiveViewMode"))
        _process_events(application, passes=3)
        assert str(surface.property("effectiveViewMode")) == expected_mode
        assert str(surface.property("requestedViewMode")) == "split"
        assert str(surface.property("selectedActivityId")) == "task-1"
        assert bool(overflow.property("visible")) is (width < 1360)
        assert float(surface.property("gridWidth")) >= 0
        assert float(surface.property("timelineWidth")) >= 0

    view.close()
    panel.deleteLater()
    _process_events(application)


def test_preference_restore_and_changes_never_invoke_business_work() -> None:
    saved: list[dict[str, object]] = []

    class Store:
        def load_gantt_view_state(self, **_kwargs):
            return {
                "requestedViewMode": "timeline",
                "splitRatio": 0.58,
                "timescale": "month",
                "zoomMultiplier": 0.875,
                "dependencyLinesEnabled": False,
                "highlightCriticalTasks": False,
            }

        def save_gantt_view_state(self, state, **_kwargs):
            saved.append(dict(state))

    def forbidden_business_work(*_args, **_kwargs):
        raise AssertionError("Gantt preferences must not trigger business work")

    signal = SimpleNamespace(emit=lambda: None)
    axis = GanttTimeAxisController()
    axis.set_projection(_projection(10))
    controller = SimpleNamespace(
        _app_settings=Store(),
        _active_organization_id_for_settings=lambda: "org-a",
        _gantt_time_axis=axis,
        _gantt_requested_view_mode="split",
        _gantt_split_ratio=0.5,
        _show_dependency_lines=True,
        _highlight_critical_tasks=True,
        ganttRequestedViewModeChanged=signal,
        ganttSplitRatioChanged=signal,
        refresh=forbidden_business_work,
        runCpm=forbidden_business_work,
        recalculateSchedule=forbidden_business_work,
    )

    gantt_view_state.restore_gantt_view_preferences(controller)
    assert controller._gantt_requested_view_mode == "timeline"
    assert controller._gantt_split_ratio == pytest.approx(0.58)
    assert controller._gantt_time_axis.timescale == "month"
    assert controller._gantt_time_axis.zoomMultiplier == pytest.approx(0.875)
    assert controller._show_dependency_lines is False
    assert controller._highlight_critical_tasks is False
    assert saved == []

    gantt_view_state.set_gantt_requested_view_mode(controller, "grid")
    gantt_view_state.set_gantt_requested_view_mode(controller, "grid")
    gantt_view_state.set_gantt_split_ratio(controller, 0.6)
    gantt_view_state.set_gantt_split_ratio(controller, 0.6)
    gantt_view_state.set_gantt_timescale(controller, "quarter")
    gantt_view_state.set_gantt_timescale(controller, "quarter")
    gantt_view_state.gantt_zoom_in(controller)
    assert len(saved) == 4


def test_keyboard_navigation_uses_effective_indexes_and_reveals_offscreen_rows() -> None:
    projection = _projection(5_000)
    model = GanttListModel()
    model.set_projection(projection)
    axis = GanttTimeAxisController()
    axis.set_projection(projection)
    application, _engine, view, surface = _create_view(
        GANTT_ROOT / "SchedulingGanttSurface.qml",
        width=1280,
        height=720,
        initial_properties={
            "ganttModel": model,
            "axisModel": axis,
            "selectedActivityId": model.taskIdAt(0),
            "requestedViewMode": "split",
        },
    )
    rows_view = surface.findChild(QObject, "ganttRowsVerticalAuthority")
    assert rows_view is not None
    selected: list[str] = []
    activated: list[str] = []

    def apply_selection(task_id: str) -> None:
        selected.append(task_id)
        surface.setProperty("selectedActivityId", task_id)

    surface.activitySelected.connect(apply_selection)
    surface.activityActivated.connect(activated.append)
    rows_view.forceActiveFocus()
    QTest.keyClick(view, Qt.Key_Down)
    _process_events(application)
    assert selected[-1] == model.taskIdAt(1)

    QTest.keyClick(view, Qt.Key_End)
    _process_events(application)
    assert selected[-1] == model.taskIdAt(model.rowCountValue - 1)
    assert float(rows_view.property("contentY")) > 0

    QTest.keyClick(view, Qt.Key_Home)
    _process_events(application)
    assert selected[-1] == model.taskIdAt(0)
    QTest.keyClick(view, Qt.Key_Return)
    _process_events(application)
    assert activated[-1] == model.taskIdAt(0)
    assert int(surface.property("activeDelegateCount")) < 100

    view.close()
    surface.deleteLater()
    _process_events(application)


def test_hierarchy_keyboard_expands_collapses_and_moves_to_parent() -> None:
    root_task = _task("root", code="ROOT", wbs="1")
    phase = _task("phase", code="PHASE", wbs="1.1", parent_id="root")
    package = _task("package", code="PKG", wbs="1.1.1", parent_id="phase")
    leaf = _task("leaf", code="LEAF", wbs="1.1.1.1", parent_id="package")
    model = GanttListModel()
    model.set_projection(_projection_from_hierarchy(root_task, phase, package, leaf))
    application, _engine, view, surface = _create_view(
        GANTT_ROOT / "SchedulingGanttSurface.qml",
        width=1280,
        height=720,
        initial_properties={"ganttModel": model, "selectedActivityId": "package"},
    )
    rows_view = surface.findChild(QObject, "ganttRowsVerticalAuthority")
    assert rows_view is not None

    def apply_selection(task_id: str) -> None:
        surface.setProperty("selectedActivityId", task_id)

    def apply_expansion(task_id: str, expanded: bool) -> None:
        model.set_expanded(task_id, expanded)

    surface.activitySelected.connect(apply_selection)
    surface.hierarchyExpansionRequested.connect(apply_expansion)
    rows_view.forceActiveFocus()
    assert model.indexOfTask("leaf") == -1
    QTest.keyClick(view, Qt.Key_Right)
    _process_events(application)
    assert model.indexOfTask("leaf") >= 0
    QTest.keyClick(view, Qt.Key_Left)
    _process_events(application)
    assert model.indexOfTask("leaf") == -1

    assert surface.setProperty("selectedActivityId", "phase")
    QTest.keyClick(view, Qt.Key_Left)
    _process_events(application)
    assert str(surface.property("selectedActivityId")) == "phase"
    assert model.indexOfTask("package") == -1
    QTest.keyClick(view, Qt.Key_Left)
    _process_events(application)
    assert str(surface.property("selectedActivityId")) == "root"

    view.close()
    surface.deleteLater()
    _process_events(application)


def test_project_baseline_restore_rejects_stale_or_cross_project_ids(
    monkeypatch,
) -> None:
    stored = {"project-a": "baseline-a", "project-b": "baseline-b"}
    saved: list[tuple[str, str]] = []
    loaded: list[str] = []

    class Store:
        def load_gantt_project_baseline(self, project_id, **_kwargs):
            return stored.get(project_id, "")

        def save_gantt_project_baseline(self, project_id, baseline_id, **_kwargs):
            saved.append((project_id, baseline_id))

    signal = SimpleNamespace(emit=lambda: None)
    controller = SimpleNamespace(
        _selected_project_id="project-a",
        _gantt_selected_baseline_id="",
        _baseline_options=[{"value": "baseline-a"}],
        _app_settings=Store(),
        _active_organization_id_for_settings=lambda: "org-a",
        ganttSelectedBaselineIdChanged=signal,
    )
    monkeypatch.setattr(
        baseline_actions,
        "_load_gantt_baseline",
        lambda _controller, baseline_id: loaded.append(baseline_id),
    )

    baseline_actions.restore_gantt_baseline_after_workspace(controller)
    assert loaded == ["baseline-a"]
    controller._selected_project_id = "project-b"
    controller._gantt_selected_baseline_id = ""
    controller._baseline_options = [{"value": "another-baseline"}]
    baseline_actions.restore_gantt_baseline_after_workspace(controller)
    assert controller._gantt_selected_baseline_id == ""
    assert saved[-1] == ("project-b", "")
    assert loaded == ["baseline-a"]


@pytest.mark.parametrize("row_count", (100, 1_000, 5_000))
def test_combined_baseline_dependency_zoom_and_scroll_remain_bounded(
    row_count: int,
) -> None:
    projection_started = perf_counter()
    projection = _combined_projection(row_count)
    projection_ms = (perf_counter() - projection_started) * 1_000
    controller = ProjectManagementSchedulingWorkspaceController()
    controller._selected_project_id = projection.project_id
    model = controller._gantt_model
    model_started = perf_counter()
    model.set_projection(projection)
    model_ms = (perf_counter() - model_started) * 1_000
    axis = controller._gantt_time_axis
    axis.set_projection(projection)
    axis.restoreConfiguration("month", 0.875)
    selected_task_id = next(row.task_id for row in projection.rows if not row.is_summary)
    controller.selectActivity(selected_task_id)
    controller._gantt_selected_baseline_id = str(projection.selected_baseline_id or "")

    viewport_started = perf_counter()
    application, _engine, view, panel = _create_view(
        SCHEDULING_ROOT / "panels" / "SchedulingGanttPanel.qml",
        width=1920,
        height=900,
        initial_properties={
            "workspaceController": controller,
            "selectedActivityModel": controller.selectedActivity,
            "ganttViewMode": "split",
        },
    )
    viewport_ms = (perf_counter() - viewport_started) * 1_000
    surface = panel.findChild(QObject, "schedulingGanttSurface")
    assert surface is not None
    rows_view = surface.findChild(QObject, "ganttRowsVerticalAuthority")
    timeline = surface.findChild(QObject, "ganttTimelineHorizontalAuthority")
    assert rows_view is not None and timeline is not None
    active_delegates = int(surface.property("activeDelegateCount"))

    scroll_started = perf_counter()
    assert rows_view.setProperty("contentY", min(2_000.0, row_count * 18.0))
    assert timeline.setProperty("contentX", 120.0)
    _process_events(application)
    scroll_ms = (perf_counter() - scroll_started) * 1_000

    zoom_started = perf_counter()
    assert axis.restoreConfiguration("month", 1.0)
    _process_events(application)
    zoom_ms = (perf_counter() - zoom_started) * 1_000

    assert bool(panel.property("inspectorInline")) is True
    assert model.baselineTaskCount == row_count - row_count // 50
    assert model.baselineOrphanTaskCount == 0
    assert 0 < active_delegates < 100
    assert int(surface.property("dependencyCandidateEdgeCount")) < 100
    assert projection_ms < 3_000
    assert model_ms < 3_000
    assert viewport_ms < 1_500
    assert scroll_ms < 500
    assert zoom_ms < 100
    print(
        "R4.5G combined "
        f"rows={row_count} projection_ms={projection_ms:.3f} model_ms={model_ms:.3f} "
        f"viewport_ms={viewport_ms:.3f} delegates={active_delegates} "
        f"scroll_ms={scroll_ms:.3f} zoom_ms={zoom_ms:.3f} "
        f"visible_edges={surface.property('dependencyCandidateEdgeCount')}"
    )

    view.close()
    panel.deleteLater()
    _process_events(application)


@pytest.mark.parametrize("row_count", (100, 1_000, 5_000))
def test_python_visible_projection_and_model_memory_remains_bounded(
    row_count: int,
) -> None:
    gc.collect()
    tracemalloc.start()
    projection = _combined_projection(row_count)
    model = GanttListModel()
    model.set_projection(projection)
    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert model.rowCountValue == row_count
    assert peak_bytes < 256 * 1024 * 1024
    print(
        "R4.5G memory "
        f"rows={row_count} current_mib={current_bytes / 1024 / 1024:.3f} "
        f"peak_mib={peak_bytes / 1024 / 1024:.3f}"
    )


def test_project_switch_replaces_large_combined_model_without_stale_indexes() -> None:
    project_a = _combined_projection(5_000, project_id="project-a", prefix="a")
    project_b = _combined_projection(100, project_id="project-b", prefix="b")
    project_c = _combined_projection(1_000, project_id="project-c", prefix="c")
    model = GanttListModel()
    model.set_projection(project_a)
    project_a_task_id = next(row.task_id for row in project_a.rows if not row.is_summary)
    assert model.indexOfTask(project_a_task_id) >= 0

    axis = GanttTimeAxisController()
    axis.set_projection(project_a)
    application, _engine, view, surface = _create_view(
        GANTT_ROOT / "SchedulingGanttSurface.qml",
        width=1440,
        height=900,
        initial_properties={
            "ganttModel": model,
            "axisModel": axis,
            "requestedViewMode": "split",
            "dependencyLinesEnabled": True,
        },
    )

    previous_task_id = project_a_task_id
    for projection in (project_b, project_c, project_a):
        model.set_projection(projection)
        axis.set_projection(projection)
        surface.setProperty("selectedActivityId", "")
        _process_events(application)
        first_leaf_id = next(row.task_id for row in projection.rows if not row.is_summary)
        assert model.rowCountValue == len(projection.rows)
        assert model.projection is not None
        assert model.projection.project_id == projection.project_id
        assert model.indexOfTask(first_leaf_id) >= 0
        if projection is not project_a:
            assert model.indexOfTask(previous_task_id) == -1
        assert model.baselineTaskCount == len(projection.baseline_snapshots)
        assert len(model.projection.dependency_edges) == len(projection.dependency_edges)
        assert int(surface.property("activeDelegateCount")) < 100
        assert int(surface.property("dependencyCandidateEdgeCount")) < 100
        previous_task_id = first_leaf_id

    view.close()
    surface.deleteLater()
    _process_events(application)


def test_g_hardening_does_not_add_business_or_r5_capabilities() -> None:
    panel = (SCHEDULING_ROOT / "panels" / "SchedulingGanttPanel.qml").read_text(
        encoding="utf-8"
    )
    surface = (GANTT_ROOT / "SchedulingGanttSurface.qml").read_text(encoding="utf-8")
    preferences = (
        REPO_ROOT
        / "src"
        / "ui_qml"
        / "modules"
        / "project_management"
        / "controllers"
        / "scheduling"
        / "gantt_view_state.py"
    ).read_text(encoding="utf-8")

    assert "AppWidgets.AnchoredPopup" in panel
    assert "onSplitRatioCommitted" in panel
    assert "requestedViewMode" in surface and "effectiveViewMode" in surface
    assert "contentY" not in preferences and "selectedActivity" not in preferences
    for forbidden in (
        "drag-to-reschedule",
        "resource histogram",
        "workload heatmap",
        "capacity lane",
        "runCpm",
        "recalculateSchedule",
    ):
        assert forbidden not in preferences
