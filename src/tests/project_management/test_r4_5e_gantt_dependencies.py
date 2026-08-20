from __future__ import annotations

import os
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from time import perf_counter

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QJSValue, QQmlComponent, QQmlExpression
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

from src.core.modules.project_management.api.desktop.scheduling.builders.gantt_builder import (
    build_gantt_projection,
)
from src.core.modules.project_management.api.desktop.scheduling.models import (
    GanttDependencyEdgeDto,
    GanttProjectionDto,
)
from src.tests.path_rewrites import REPO_ROOT
from src.tests.project_management.test_r4_5b_gantt_read_contract import (
    _edge,
    _node,
    _projection,
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


GANTT_ROOT = (
    REPO_ROOT
    / "src"
    / "ui_qml"
    / "modules"
    / "project_management"
    / "qml"
    / "workspaces"
    / "scheduling"
    / "components"
    / "gantt"
)


def _application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    return existing or QGuiApplication(["r4-5e-gantt-test"])


def _process_events(application: QGuiApplication, passes: int = 8) -> None:
    for _ in range(passes):
        application.processEvents()


def _variant(value):
    return value.toVariant() if isinstance(value, QJSValue) else value


def _typed_projection() -> GanttProjectionDto:
    predecessor = _task("pred", code="PRED", wbs="1")
    successor = _task("succ", code="SUCC", wbs="2")
    return build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=(_node(predecessor), _node(successor)),
        schedule_items=(
            _schedule(
                predecessor,
                start=date(2026, 1, 2),
                finish=date(2026, 1, 3),
            ),
            _schedule(
                successor,
                start=date(2026, 1, 6),
                finish=date(2026, 1, 8),
            ),
        ),
        dependency_rows=tuple(
            _edge(index, "pred", "succ", relation, lag)
            for index, (relation, lag) in enumerate(
                (("FS", -2), ("SS", 0), ("FF", 3), ("SF", 1)),
                start=1,
            )
        ),
    )


def _minimum_width_and_milestone_projection() -> GanttProjectionDto:
    predecessor = _task("pred", code="PRED", wbs="1")
    successor = _task("succ", code="MILE", wbs="2", is_milestone=True)
    return build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=(_node(predecessor), _node(successor)),
        schedule_items=(
            _schedule(
                predecessor,
                start=date(2026, 1, 2),
                finish=date(2026, 1, 2),
            ),
            _schedule(
                successor,
                start=date(2026, 1, 5),
                finish=date(2026, 1, 5),
            ),
        ),
        dependency_rows=(
            _edge(1, "pred", "succ", "FS", 0),
            _edge(2, "pred", "succ", "SF", 0),
        ),
    )


def _create_layer(model: GanttListModel, *, selected: str = "", limit: int = 500):
    application = _application()
    engine = create_qml_engine()
    view = QQuickView(engine, None)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.setInitialProperties(
        {
            "ganttModel": model,
            "firstRenderedIndex": 0,
            "lastRenderedIndex": max(0, model.rowCountValue - 1),
            "rowHeight": 36,
            "verticalContentY": 0.0,
            "axisStartDay": date(2026, 1, 1).toordinal(),
            "pixelsPerDay": 10.0,
            "selectedTaskId": selected,
            "normalEdgeLimit": limit,
        }
    )
    view.setSource(
        QUrl.fromLocalFile(str(GANTT_ROOT / "SchedulingGanttDependencyLayer.qml"))
    )
    assert view.status() == QQuickView.Ready, "\n".join(
        error.toString() for error in view.errors()
    )
    view.resize(1_200, 640)
    view.show()
    layer = view.rootObject()
    assert layer is not None
    _process_events(application)
    QTest.qWait(30)
    return application, engine, view, layer


def _routes(layer) -> list[dict[str, object]]:
    return list(_variant(layer.property("visibleRoutes")) or [])


def _dense_projection(row_count: int, edge_count: int) -> GanttProjectionDto:
    projection = _projection(row_count)
    rows = projection.rows
    relations = ("FS", "SS", "FF", "SF")
    edges: list[GanttDependencyEdgeDto] = []
    pair_index = 0
    while len(edges) < edge_count:
        predecessor_index = pair_index % row_count
        successor_index = (pair_index // row_count + predecessor_index + 1) % row_count
        if predecessor_index == successor_index:
            pair_index += 1
            continue
        predecessor = rows[predecessor_index]
        successor = rows[successor_index]
        relation = relations[len(edges) % len(relations)]
        edge_number = len(edges)
        edges.append(
            GanttDependencyEdgeDto(
                tenant_id=projection.tenant_id,
                organization_id=projection.organization_id,
                project_id=projection.project_id,
                dependency_id=f"dense-{edge_number}",
                predecessor_task_id=predecessor.task_id,
                predecessor_task_name=predecessor.name,
                successor_task_id=successor.task_id,
                successor_task_name=successor.name,
                dependency_type=relation,
                dependency_type_label=relation,
                lag_days=(edge_number % 7) - 3,
            )
        )
        pair_index += 1
    return replace(projection, dependency_edges=tuple(edges))


def _long_chain_projection(row_count: int) -> GanttProjectionDto:
    tasks = [
        _task(f"long-{index}", code=f"L-{index}", wbs=str(index + 1))
        for index in range(row_count)
    ]
    start = date(2026, 1, 1)
    return build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=tuple(_node(task) for task in tasks),
        schedule_items=tuple(
            _schedule(
                task,
                start=start + timedelta(days=index * 2),
                finish=start + timedelta(days=index * 2 + 1),
            )
            for index, task in enumerate(tasks)
        ),
        dependency_rows=tuple(
            _edge(index, tasks[index - 1].id, tasks[index].id, "FS", 0)
            for index in range(1, row_count)
        ),
    )


def test_dependency_window_uses_adjacency_and_preserves_typed_signed_metadata() -> None:
    model = GanttListModel()
    model.set_projection(_typed_projection())

    window = model.dependencyWindow(0, 1, "pred", 500)

    assert window["candidateEdgeCount"] == 4
    assert window["suppressed"] is False
    assert {edge["dependencyType"] for edge in window["edges"]} == {
        "FF", "FS", "SF", "SS"
    }
    assert sorted(edge["lagDays"] for edge in window["edges"]) == [-2, 0, 1, 3]
    assert all(edge["selected"] is True for edge in window["edges"])
    assert {edge["predecessorRowIndex"] for edge in window["edges"]} == {0}
    assert {edge["successorRowIndex"] for edge in window["edges"]} == {1}


def test_runtime_routes_use_correct_fs_ss_ff_sf_anchors_and_successor_direction() -> None:
    model = GanttListModel()
    model.set_projection(_typed_projection())
    application, _engine, _component, layer = _create_layer(model)
    by_type = {route["dependencyType"]: route for route in _routes(layer)}

    assert set(by_type) == {"FS", "SS", "FF", "SF"}
    assert (by_type["FS"]["sourceX"], by_type["FS"]["targetX"]) == (30, 50)
    assert (by_type["SS"]["sourceX"], by_type["SS"]["targetX"]) == (10, 50)
    assert (by_type["FF"]["sourceX"], by_type["FF"]["targetX"]) == (30, 80)
    assert (by_type["SF"]["sourceX"], by_type["SF"]["targetX"]) == (10, 80)
    assert by_type["FS"]["targetFinishAnchor"] is False
    assert by_type["SS"]["targetFinishAnchor"] is False
    assert by_type["FF"]["targetFinishAnchor"] is True
    assert by_type["SF"]["targetFinishAnchor"] is True
    assert {route["lagDays"] for route in by_type.values()} == {-2, 0, 1, 3}
    assert int(layer.property("paintedRouteCount")) == 4
    layer.deleteLater()
    _process_events(application)


def test_routes_attach_to_minimum_width_bars_and_milestone_sides() -> None:
    model = GanttListModel()
    model.set_projection(_minimum_width_and_milestone_projection())
    application, _engine, _view, layer = _create_layer(model)
    assert layer.setProperty("pixelsPerDay", 1.5)
    _process_events(application)
    by_type = {route["dependencyType"]: route for route in _routes(layer)}

    # The one-day predecessor is widened to 12px at Quarter-like density.
    assert by_type["FS"]["sourceX"] == pytest.approx(13.5)
    assert by_type["SF"]["sourceX"] == pytest.approx(1.5)
    milestone_center = 4.5 * 1.5
    assert by_type["FS"]["targetX"] == pytest.approx(milestone_center - 7)
    assert by_type["SF"]["targetX"] == pytest.approx(milestone_center + 7)
    layer.deleteLater()
    _process_events(application)


def test_unsupported_dependency_type_fails_visibly_instead_of_misrouting() -> None:
    projection = _typed_projection()
    invalid_edge = replace(
        projection.dependency_edges[0],
        dependency_type="XX",
        dependency_type_label="Unsupported",
    )
    model = GanttListModel()
    model.set_projection(replace(projection, dependency_edges=(invalid_edge,)))
    application, _engine, _view, layer = _create_layer(model)

    assert int(layer.property("routeCount")) == 0
    assert "Unsupported dependency type" in str(layer.property("renderError"))
    assert "unavailable" in str(layer.property("statusMessage"))
    layer.deleteLater()
    _process_events(application)


def test_filtered_collapsed_and_offscreen_endpoints_hide_complete_edge() -> None:
    summary = _task("summary", code="SUM", wbs="1")
    predecessor = _task("pred", code="PRED", wbs="1.1", parent_id="summary")
    successor = _task("succ", code="SUCC", wbs="1.2", parent_id="summary")
    projection = build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=(
            _node(summary, is_summary=True, child_count=2),
            _node(predecessor, depth=1, ancestors=("summary",)),
            _node(successor, depth=1, ancestors=("summary",)),
        ),
        schedule_items=(
            _schedule(predecessor, start=date(2026, 1, 1), finish=date(2026, 1, 2)),
            _schedule(successor, start=date(2026, 1, 3), finish=date(2026, 1, 4)),
        ),
        dependency_rows=(_edge(1, "pred", "succ", "FS", 0),),
    )
    model = GanttListModel()
    model.set_projection(projection)

    assert model.dependencyWindow(0, 2, "", 500)["candidateEdgeCount"] == 1
    assert model.dependencyWindow(0, 1, "", 500)["candidateEdgeCount"] == 0
    assert model.dependencyWindow(1, 1, "", 500)["candidateEdgeCount"] == 0

    model.apply_view(
        search_text="Pred",
        status_filter="all",
        critical_only=False,
        delayed_only=False,
        sort_key="schedule",
        sort_descending=False,
    )
    filtered = model.dependencyWindow(0, model.rowCountValue - 1, "", 500)
    assert filtered["candidateEdgeCount"] == 0

    model.apply_view(
        search_text="",
        status_filter="all",
        critical_only=False,
        delayed_only=False,
        sort_key="schedule",
        sort_descending=False,
    )
    model.set_expanded("summary", False)
    collapsed = model.dependencyWindow(0, model.rowCountValue - 1, "", 500)
    assert model.rowCountValue == 1
    assert collapsed["candidateEdgeCount"] == 0


def test_flat_sort_recomputes_endpoint_rows_without_changing_edge_semantics() -> None:
    model = GanttListModel()
    model.set_projection(_typed_projection())
    model.apply_view(
        search_text="",
        status_filter="all",
        critical_only=False,
        delayed_only=False,
        sort_key="taskName",
        sort_descending=True,
    )

    window = model.dependencyWindow(0, 1, "", 500)
    edge = window["edges"][0]
    assert model.taskIdAt(0) == "succ"
    assert edge["predecessorRowIndex"] == 1
    assert edge["successorRowIndex"] == 0
    assert edge["predecessorTaskId"] == "pred"
    assert edge["successorTaskId"] == "succ"


def test_toggle_off_skips_window_collection_and_clears_routes() -> None:
    class CountingModel(GanttListModel):
        def __init__(self) -> None:
            super().__init__()
            self.window_calls = 0

        def dependencyWindow(self, *args):
            self.window_calls += 1
            return super().dependencyWindow(*args)

    model = CountingModel()
    model.set_projection(_typed_projection())
    application, _engine, _component, layer = _create_layer(model)
    assert model.window_calls > 0
    calls_before_off = model.window_calls

    assert layer.setProperty("dependencyLinesEnabled", False)
    assert layer.setProperty("selectedTaskId", "pred")
    assert layer.setProperty("pixelsPerDay", 12.0)
    _process_events(application)

    assert model.window_calls == calls_before_off
    assert int(layer.property("routeCount")) == 0
    assert int(layer.property("paintedRouteCount")) == 0
    layer.deleteLater()
    _process_events(application)


def test_selection_emphasizes_only_incident_edges_without_refresh_or_cpm() -> None:
    projection = _projection(4, with_edges=True)
    controller = ProjectManagementSchedulingWorkspaceController()
    controller._gantt_model.set_projection(projection)
    controller.refresh = lambda: (_ for _ in ()).throw(
        AssertionError("Dependency selection must not refresh, query, or rerun CPM")
    )
    application, _engine, _component, layer = _create_layer(controller._gantt_model)

    controller.selectActivity("task-1")
    assert layer.setProperty("selectedTaskId", controller.selectedActivityId)
    _process_events(application)
    selected = {route["dependencyId"] for route in _routes(layer) if route["selected"]}
    assert selected == {"edge-1", "edge-2"}

    controller.selectActivity("task-3")
    assert layer.setProperty("selectedTaskId", controller.selectedActivityId)
    _process_events(application)
    selected = {route["dependencyId"] for route in _routes(layer) if route["selected"]}
    assert selected == {"edge-3"}

    controller.selectActivity("")
    assert layer.setProperty("selectedTaskId", "")
    _process_events(application)
    assert not any(route["selected"] for route in _routes(layer))
    layer.deleteLater()
    _process_events(application)


def test_project_switch_replaces_route_cache_without_stale_edge_flash() -> None:
    model = GanttListModel()
    model.set_projection(_typed_projection())
    application, _engine, _component, layer = _create_layer(model)
    assert {route["dependencyId"] for route in _routes(layer)} == {
        "edge-1",
        "edge-2",
        "edge-3",
        "edge-4",
    }

    replacement = _projection(3, with_edges=True)
    replacement = replace(
        replacement,
        project_id="project-2",
        rows=tuple(replace(row, project_id="project-2") for row in replacement.rows),
        dependency_edges=tuple(
            replace(edge, project_id="project-2")
            for edge in replacement.dependency_edges
        ),
    )
    model.set_projection(replacement)
    assert int(layer.property("routeCount")) == 0
    assert layer.setProperty("lastRenderedIndex", 2)
    _process_events(application)

    assert {route["dependencyId"] for route in _routes(layer)} == {"edge-1", "edge-2"}
    assert _variant(layer.property("visibleRoutes"))[0]["predecessorTaskId"].startswith("task-")
    layer.deleteLater()
    _process_events(application)


def test_integrated_surface_keeps_routes_aligned_across_view_state_changes() -> None:
    application = _application()
    engine = create_qml_engine()
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str(GANTT_ROOT / "SchedulingGanttSurface.qml")),
    )
    surface = component.create()
    assert surface is not None, "\n".join(error.toString() for error in component.errors())
    projection = _long_chain_projection(100)
    model = GanttListModel()
    model.set_projection(projection)
    axis = GanttTimeAxisController(today_provider=lambda: date(2026, 4, 1))
    axis.set_projection(projection)

    assert surface.setProperty("width", 1_280)
    assert surface.setProperty("height", 640)
    assert surface.setProperty("requestedViewMode", "timeline")
    assert surface.setProperty("ganttModel", model)
    assert surface.setProperty("axisModel", axis)
    _process_events(application)
    layer = surface.findChild(QObject, "ganttDependencyLayer")
    rows_view = surface.findChild(QObject, "ganttRowsVerticalAuthority")
    timeline = surface.findChild(QObject, "ganttTimelineHorizontalAuthority")
    assert layer is not None and rows_view is not None and timeline is not None
    initial_routes = _variant(layer.property("visibleRoutes"))
    initial_ids = {route["dependencyId"] for route in initial_routes}
    assert initial_ids

    assert rows_view.setProperty("contentY", 1_200.0)
    _process_events(application)
    scrolled_routes = _variant(layer.property("visibleRoutes"))
    scrolled_ids = {route["dependencyId"] for route in scrolled_routes}
    assert scrolled_ids
    assert scrolled_ids != initial_ids

    before_pan = list(scrolled_routes)
    assert timeline.setProperty("contentX", 240.0)
    _process_events(application)
    assert _variant(layer.property("visibleRoutes")) == before_pan

    expression = QQmlExpression(engine.rootContext(), surface, "zoomIn()")
    value, is_undefined = expression.evaluate()
    assert value is True and is_undefined is False
    _process_events(application)
    zoomed = _variant(layer.property("visibleRoutes"))
    assert zoomed[0]["sourceX"] != before_pan[0]["sourceX"]

    for scale in ("day", "week", "month", "quarter"):
        expression = QQmlExpression(
            engine.rootContext(), surface, f"setTimescale('{scale}')"
        )
        value, is_undefined = expression.evaluate()
        assert value is True and is_undefined is False
        _process_events(application)
        routes = _variant(layer.property("visibleRoutes"))
        assert {route["dependencyId"] for route in routes} == scrolled_ids

    assert surface.setProperty("requestedViewMode", "grid")
    _process_events(application)
    assert int(layer.property("routeCount")) == 0
    assert surface.setProperty("requestedViewMode", "timeline")
    _process_events(application)
    assert int(layer.property("routeCount")) > 0
    surface.deleteLater()
    _process_events(application)


def test_scroll_zoom_and_scale_only_rebuild_display_routes() -> None:
    model = GanttListModel()
    model.set_projection(_typed_projection())
    application, _engine, _component, layer = _create_layer(model)
    original = {route["dependencyId"]: route for route in _routes(layer)}

    assert layer.setProperty("timelineContentX", 120.0)
    assert layer.setProperty("verticalContentY", 12.0)
    _process_events(application)
    panned = {route["dependencyId"]: route for route in _routes(layer)}
    assert panned == original

    assert layer.setProperty("pixelsPerDay", 20.0)
    _process_events(application)
    zoomed = {route["dependencyId"]: route for route in _routes(layer)}
    assert zoomed["edge-1"]["sourceX"] == original["edge-1"]["sourceX"] * 2
    assert zoomed["edge-1"]["targetX"] == original["edge-1"]["targetX"] * 2
    layer.deleteLater()
    _process_events(application)


@pytest.mark.parametrize("row_count", [100, 1_000, 5_000])
def test_visible_edge_lookup_is_bounded_by_row_window(row_count: int) -> None:
    model = GanttListModel()
    model.set_projection(_projection(row_count, with_edges=True))

    started = perf_counter()
    window = model.dependencyWindow(0, 29, "task-10", 500)
    elapsed_ms = (perf_counter() - started) * 1_000

    print(
        f"R4.5E lookup rows={row_count} project_edges={row_count - 1} "
        f"visible_edges={window['candidateEdgeCount']} elapsed_ms={elapsed_ms:.3f}"
    )
    assert elapsed_ms < 50
    assert window["candidateEdgeCount"] == min(29, row_count - 1)


def test_measured_density_fallback_is_visible_and_keeps_selected_incident_edges() -> None:
    model = GanttListModel()
    model.set_projection(_dense_projection(50, 9_800))
    application, _engine, _component, layer = _create_layer(
        model, selected="task-0", limit=500
    )

    assert bool(layer.property("densitySuppressed")) is True
    assert int(layer.property("candidateEdgeCount")) == 9_800
    assert 0 < int(layer.property("routeCount")) < 500
    assert all(route["selected"] is True for route in _routes(layer))
    assert "limited for performance" in str(layer.property("statusMessage"))
    assert float(layer.property("lastRouteBuildMs")) < 50
    assert float(layer.property("lastPaintMs")) < 50
    print(
        "R4.5E dense edges=9800 "
        f"selected_routes={layer.property('routeCount')} "
        f"route_ms={layer.property('lastRouteBuildMs')} "
        f"paint_ms={layer.property('lastPaintMs')}"
    )
    layer.deleteLater()
    _process_events(application)


@pytest.mark.parametrize("edge_count", [100, 500, 1_000, 5_000, 9_800])
def test_dependency_route_and_paint_characterization(edge_count: int) -> None:
    model = GanttListModel()
    model.set_projection(_dense_projection(50, edge_count))
    application, _engine, _component, layer = _create_layer(model, limit=0)

    route_ms = float(layer.property("lastRouteBuildMs"))
    paint_ms = float(layer.property("lastPaintMs"))
    print(
        f"R4.5E paint edges={edge_count} routes={layer.property('routeCount')} "
        f"route_ms={route_ms:.3f} paint_ms={paint_ms:.3f}"
    )
    assert int(layer.property("routeCount")) == edge_count
    if edge_count <= 500:
        assert route_ms < 50
        assert paint_ms < 50
    layer.deleteLater()
    _process_events(application)


def test_dependency_canvas_architecture_has_one_bounded_renderer() -> None:
    layer = (GANTT_ROOT / "SchedulingGanttDependencyLayer.qml").read_text(
        encoding="utf-8"
    )
    surface = (GANTT_ROOT / "SchedulingGanttSurface.qml").read_text(encoding="utf-8")
    row = (GANTT_ROOT / "SchedulingGanttRow.qml").read_text(encoding="utf-8")

    assert layer.count("Canvas {") == 1
    assert "Repeater" not in layer
    assert "ShapePath" not in layer
    assert "devicePixelRatio" in layer
    assert "dependencyWindow(" in layer
    assert surface.count("SchedulingGanttDependencyLayer {") == 1
    assert "SchedulingGanttDependencyLayer" not in row
    for forbidden in (
        "createDependency",
        "updateDependency",
        "deleteDependency",
        "recalculate",
        "runCpm",
        "baseline",
    ):
        assert forbidden not in layer
