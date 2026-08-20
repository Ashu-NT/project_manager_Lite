from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from time import perf_counter

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent

from src.core.modules.project_management.api.desktop.scheduling.builders.gantt_builder import (
    build_gantt_projection,
)
from src.tests.path_rewrites import REPO_ROOT
from src.tests.project_management.test_r4_5b_gantt_read_contract import (
    _node,
    _projection,
    _schedule,
    _task,
)
from src.ui_qml.modules.project_management.controllers.scheduling.gantt_list_model import (
    GanttListModel,
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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    return existing or QGuiApplication(["r4-5c-gantt-test"])


def test_integrated_surface_has_one_row_viewport_and_no_legacy_renderer() -> None:
    panel = _read(SCHEDULING_ROOT / "panels" / "SchedulingGanttPanel.qml")
    surface = _read(GANTT_ROOT / "SchedulingGanttSurface.qml")
    viewport = _read(GANTT_ROOT / "SchedulingGanttRowsViewport.qml")
    row = _read(GANTT_ROOT / "SchedulingGanttRow.qml")

    assert viewport.count("ListView {") == 1
    assert "model: root.ganttModel" in viewport
    assert "reuseItems: true" in viewport
    assert "Repeater" not in viewport
    assert "SchedulingGanttRow" in viewport
    assert "gridWidth" in row and "timelineWidth" in row
    assert "contentY" not in surface
    assert "TablePaginationBar" not in panel
    assert "AppWidgets.DataTable" not in panel
    assert not (SCHEDULING_ROOT / "panels" / "SchedulingTimelinePanel.qml").exists()
    assert not (
        REPO_ROOT
        / "src"
        / "ui_qml"
        / "modules"
        / "project_management"
        / "controllers"
        / "scheduling"
        / "gantt_legacy_adapter.py"
    ).exists()


def test_compact_inspector_has_one_header_and_activity_id_is_user_facing() -> None:
    panel = _read(SCHEDULING_ROOT / "panels" / "SchedulingGanttPanel.qml")
    inspector = _read(
        REPO_ROOT / "src" / "ui_qml" / "shared" / "qml" / "App" / "Widgets"
        / "InspectorPanel.qml"
    )
    task_id = "7f05d925-0053-4149-a554-aa928d0462c7"
    task = _task(task_id, code="TASK-042", wbs="4.2")
    controller = ProjectManagementSchedulingWorkspaceController()

    controller._gantt_model.set_projection(
        build_gantt_projection(
            tenant_id="tenant-1",
            organization_id="org-1",
            project_id="project-1",
            hierarchy_nodes=(_node(task),),
            schedule_items=(
                _schedule(task, start=date(2026, 1, 1), finish=date(2026, 1, 2)),
            ),
        )
    )
    controller.selectActivity(task_id)

    fields = controller.selectedActivity["fields"]
    assert [field["label"] for field in fields].count("Activity ID") == 1
    assert all(field["label"] != "Activity code" for field in fields)
    assert fields[0]["value"] == "TASK-042"
    assert task_id not in {field["value"] for field in fields}
    assert "property bool showHeader: true" in inspector
    assert "showHeader: !root.compact" in panel


def test_open_task_uses_canonical_pm_entity_navigation() -> None:
    scheduling_page = _read(SCHEDULING_ROOT / "SchedulingWorkspacePage.qml")
    tasks_page = _read(
        SCHEDULING_ROOT.parent / "tasks" / "TasksWorkspacePage.qml"
    )
    qmltypes = _read(
        REPO_ROOT / "src" / "ui_qml" / "modules" / "project_management" / "qml"
        / "ProjectManagement" / "Controllers" / "typeinfo" / "plugins.qmltypes"
    )

    assert 'root.pmNavigation.openEntity("tasks", activityId, "")' in scheduling_page
    assert 'selectRoute("project_management.tasks")' not in scheduling_page
    assert "function _applyPmNavigationIntent()" in tasks_page
    assert "root.workspaceController.activateTask(taskId)" in tasks_page
    assert (
        "root._openDetail(root._navigationSectionIndex(routeState.section))"
        in tasks_page
    )
    assert 'name: "PMWorkspaceNavigationController"' in qmltypes
    assert 'Property { name: "pmNavigation"' in qmltypes


def test_hierarchy_expansion_and_selection_use_the_indexed_effective_rows() -> None:
    root_task = _task("root", code="ROOT", wbs="1")
    phase = _task("phase", code="PHASE", wbs="1.1", parent_id="root")
    package = _task("package", code="PKG", wbs="1.1.1", parent_id="phase")
    leaf = _task("leaf", code="LEAF", wbs="1.1.1.1", parent_id="package")
    projection = _projection_from_hierarchy(root_task, phase, package, leaf)
    controller = ProjectManagementSchedulingWorkspaceController()
    controller._gantt_model.set_projection(projection)

    assert [row.task_id for row in controller._gantt_model.effective_rows] == [
        "root",
        "phase",
        "package",
    ]
    assert controller._gantt_model.indexOfTask("package") == 2
    assert controller._gantt_model.indexOfTask("leaf") == -1

    controller.setGanttExpanded("package", True)
    controller.selectActivity("leaf")
    assert controller.selectedActivityId == "leaf"
    assert controller.selectedActivity["taskId"] == "leaf"

    controller.setGanttExpanded("package", False)
    assert controller.selectedActivityId == ""
    assert controller.selectedActivity["taskId"] == ""

    controller.setActivitySort("taskName", 0)
    assert controller.ganttRowsModel.hierarchyMode is False
    assert all(
        controller.ganttRowsModel.data(
            controller.ganttRowsModel.index(index, 0),
            controller.ganttRowsModel.DepthRole,
        )
        == 0
        for index in range(controller.ganttRowsModel.rowCountValue)
    )


@pytest.mark.parametrize("row_count", [100, 1_000, 5_000])
def test_surface_runtime_is_responsive_and_virtualizes_rows(row_count: int) -> None:
    application = _application()
    engine = create_qml_engine()
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str(GANTT_ROOT / "SchedulingGanttSurface.qml")),
    )
    surface = component.create()
    assert surface is not None, "\n".join(error.toString() for error in component.errors())

    model = GanttListModel()
    attach_started = perf_counter()
    projection = _projection(row_count)
    model.set_projection(projection)
    model_attach_ms = (perf_counter() - attach_started) * 1_000

    viewport_started = perf_counter()
    assert surface.setProperty("width", 1024)
    assert surface.setProperty("height", 640)
    assert surface.setProperty("requestedViewMode", "split")
    assert surface.setProperty("ganttModel", model)
    assert surface.setProperty(
        "columns",
        [
            {"key": "wbs", "label": "WBS", "minWidth": 72, "visible": True},
            {
                "key": "taskName",
                "label": "Task Name",
                "minWidth": 220,
                "visible": True,
            },
        ],
    )
    application.processEvents()
    first_viewport_ms = (perf_counter() - viewport_started) * 1_000

    assert surface.property("effectiveViewMode") == "grid"
    active_delegates = int(surface.property("activeDelegateCount"))
    assert 0 < active_delegates < 100

    assert surface.setProperty("width", 1280)
    mode_started = perf_counter()
    application.processEvents()
    mode_switch_ms = (perf_counter() - mode_started) * 1_000
    assert surface.property("effectiveViewMode") == "split"
    assert int(surface.property("activeDelegateCount")) < 100

    rows_view = surface.findChild(QObject, "ganttRowsVerticalAuthority")
    timeline_axis = surface.findChild(QObject, "ganttTimelineHorizontalAuthority")
    assert rows_view is not None
    assert timeline_axis is not None
    scroll_started = perf_counter()
    assert rows_view.setProperty("contentY", 2_000)
    application.processEvents()
    scroll_ms = (perf_counter() - scroll_started) * 1_000
    assert float(rows_view.property("contentY")) > 0

    filter_started = perf_counter()
    model.apply_view(
        search_text=f"Task {row_count - 1}",
        status_filter="all",
        critical_only=False,
        delayed_only=False,
        sort_key="schedule",
        sort_descending=False,
    )
    application.processEvents()
    filter_ms = (perf_counter() - filter_started) * 1_000

    controller = ProjectManagementSchedulingWorkspaceController()
    controller._gantt_model.set_projection(projection)
    selection_started = perf_counter()
    controller.selectActivity(f"task-{row_count - 1}")
    selection_ms = (perf_counter() - selection_started) * 1_000

    print(
        "R4.5C viewport "
        f"rows={row_count} model_attach_ms={model_attach_ms:.3f} "
        f"first_viewport_ms={first_viewport_ms:.3f} delegates={active_delegates} "
        f"selection_ms={selection_ms:.3f} scroll_ms={scroll_ms:.3f} "
        f"filter_ms={filter_ms:.3f} mode_switch_ms={mode_switch_ms:.3f}"
    )

    assert model_attach_ms < 3_000
    assert first_viewport_ms < 1_500
    assert selection_ms < 50
    assert scroll_ms < 500
    assert filter_ms < 500
    assert mode_switch_ms < 500

    surface.deleteLater()
    application.processEvents()


def test_indexed_selection_and_local_filter_remain_below_interaction_budget() -> None:
    controller = ProjectManagementSchedulingWorkspaceController()
    controller._gantt_model.set_projection(_projection(5_000))
    controller.refresh = lambda: (_ for _ in ()).throw(
        AssertionError("UI-only Gantt interaction must not refresh or run CPM")
    )

    selection_started = perf_counter()
    controller.selectActivity("task-4999")
    selection_ms = (perf_counter() - selection_started) * 1_000

    filter_started = perf_counter()
    controller.setSearchText("Task 4999")
    filter_ms = (perf_counter() - filter_started) * 1_000

    assert selection_ms < 50
    assert filter_ms < 500
    assert controller.selectedActivityId == "task-4999"
    assert controller.ganttRowsModel.rowCountValue == 1


def _projection_from_hierarchy(root_task, phase, package, leaf):
    from datetime import date

    from src.core.modules.project_management.api.desktop.scheduling.builders.gantt_builder import (
        build_gantt_projection,
    )

    nodes = (
        _node(root_task, depth=0, is_summary=True, child_count=1),
        _node(phase, depth=1, is_summary=True, child_count=1, ancestors=("root",)),
        _node(
            package,
            depth=2,
            is_summary=True,
            child_count=1,
            ancestors=("root", "phase"),
        ),
        _node(leaf, depth=3, ancestors=("root", "phase", "package")),
    )
    return build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=nodes,
        schedule_items=(
            _schedule(leaf, start=date(2026, 1, 1), finish=date(2026, 1, 2)),
        ),
    )
