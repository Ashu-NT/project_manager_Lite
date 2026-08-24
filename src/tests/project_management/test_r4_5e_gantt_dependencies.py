from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from time import perf_counter

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QColor, QGuiApplication
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


def _create_layer(
    model: GanttListModel,
    *,
    selected: str = "",
    limit: int = 500,
    connector_color: QColor | None = None,
):
    application = _application()
    engine = create_qml_engine()
    view = QQuickView(engine, None)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    initial_properties = {
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
    if connector_color is not None:
        initial_properties["normalConnectorColor"] = connector_color
        initial_properties["selectedConnectorColor"] = connector_color
    view.setInitialProperties(initial_properties)
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


def _painted_red_bounds(image) -> list[int]:
    points: list[tuple[int, int]] = []
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.red() >= 200 and color.green() <= 150 and color.blue() <= 150:
                points.append((x, y))
    if not points:
        raise AssertionError("Dependency Canvas produced no red painted pixels")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [min(xs), min(ys), max(xs), max(ys), len(points)]


def _has_red_near(image, x: float, y: float, pixel_scale: float) -> bool:
    center_x = round(x * pixel_scale)
    center_y = round(y * pixel_scale)
    radius = max(2, round(2 * pixel_scale))
    for pixel_y in range(max(0, center_y - radius), min(image.height(), center_y + radius + 1)):
        for pixel_x in range(max(0, center_x - radius), min(image.width(), center_x + radius + 1)):
            color = image.pixelColor(pixel_x, pixel_y)
            if color.red() >= 200 and color.green() <= 150 and color.blue() <= 150:
                return True
    return False


def _canvas_paint_probe() -> dict[str, object]:
    predecessor = _task("pred", code="PRED", wbs="1")
    successor = _task("succ", code="SUCC", wbs="2")
    projection = build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=(_node(predecessor), _node(successor)),
        schedule_items=(
            _schedule(
                predecessor,
                start=date(2026, 8, 10),
                finish=date(2026, 8, 12),
            ),
            _schedule(
                successor,
                start=date(2026, 8, 15),
                finish=date(2026, 8, 18),
            ),
        ),
        dependency_rows=(_edge(1, "pred", "succ", "FS", 0),),
    )
    model = GanttListModel()
    model.set_projection(projection)
    application, _engine, view, layer = _create_layer(
        model,
        connector_color=QColor("#ff0000"),
    )
    view.setColor(QColor("#ffffff"))
    view.resize(240, 100)
    assert layer.setProperty("axisStartDay", date(2026, 8, 1).toordinal())
    assert layer.setProperty("pixelsPerDay", 12.0)

    def snapshot() -> tuple[object, list[int]]:
        _process_events(application)
        QTest.qWait(40)
        image = view.grabWindow()
        return image, _painted_red_bounds(image)

    initial_image, initial = snapshot()
    initial_routes = _routes(layer)
    route = initial_routes[0]
    assert layer.setProperty("timelineContentX", 100.0)
    horizontal_image, horizontal = snapshot()
    assert _routes(layer) == initial_routes
    assert layer.setProperty("timelineContentX", 250.0)
    _process_events(application)
    QTest.qWait(40)
    try:
        _painted_red_bounds(view.grabWindow())
        fully_offscreen_clipped = False
    except AssertionError:
        fully_offscreen_clipped = True
    assert _routes(layer) == initial_routes
    assert layer.setProperty("timelineContentX", 100.0)
    assert layer.setProperty("verticalContentY", 12.0)
    vertical_image, vertical = snapshot()
    assert _routes(layer) == initial_routes
    assert layer.setProperty("verticalContentY", 20.0)
    assert layer.setProperty("verticalOriginY", 8.0)
    generalized_origin_image, generalized_origin = snapshot()
    assert _routes(layer) == initial_routes

    pixel_scale = float(initial_image.width()) / float(view.width())
    endpoint_alignment = {
        "initialSource": _has_red_near(
            initial_image, float(route["sourceX"]), float(route["sourceY"]), pixel_scale
        ),
        "initialTarget": _has_red_near(
            initial_image, float(route["targetX"]), float(route["targetY"]), pixel_scale
        ),
        "horizontalSource": _has_red_near(
            horizontal_image,
            float(route["sourceX"]) - 100.0,
            float(route["sourceY"]),
            pixel_scale,
        ),
        "horizontalTarget": _has_red_near(
            horizontal_image,
            float(route["targetX"]) - 100.0,
            float(route["targetY"]),
            pixel_scale,
        ),
        "verticalSource": _has_red_near(
            vertical_image,
            float(route["sourceX"]) - 100.0,
            float(route["sourceY"]) - 12.0,
            pixel_scale,
        ),
        "verticalTarget": _has_red_near(
            vertical_image,
            float(route["targetX"]) - 100.0,
            float(route["targetY"]) - 12.0,
            pixel_scale,
        ),
        "generalizedOriginSource": _has_red_near(
            generalized_origin_image,
            float(route["sourceX"]) - 100.0,
            float(route["sourceY"]) - 12.0,
            pixel_scale,
        ),
        "generalizedOriginTarget": _has_red_near(
            generalized_origin_image,
            float(route["targetX"]) - 100.0,
            float(route["targetY"]) - 12.0,
            pixel_scale,
        ),
    }

    result = {
        "devicePixelRatio": float(view.devicePixelRatio()),
        "pixelScale": pixel_scale,
        "initial": initial,
        "horizontal": horizontal,
        "vertical": vertical,
        "generalizedOrigin": generalized_origin,
        "fullyOffscreenClipped": fully_offscreen_clipped,
        "endpointAlignment": endpoint_alignment,
        "sourceX": float(route["sourceX"]),
        "targetX": float(route["targetX"]),
        "sourceY": float(route["sourceY"]),
        "targetY": float(route["targetY"]),
    }
    view.close()
    layer.deleteLater()
    _process_events(application)
    return result


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


@pytest.mark.parametrize(
    ("timescale", "base_pixels_per_day"),
    (("day", 40.0), ("week", 12.0), ("month", 4.0), ("quarter", 1.5)),
)
def test_all_timescales_and_zoom_levels_share_exact_dependency_anchor_geometry(
    timescale: str,
    base_pixels_per_day: float,
) -> None:
    model = GanttListModel()
    model.set_projection(_typed_projection())
    application, _engine, _view, layer = _create_layer(model)

    for zoom in (0.75, 0.875, 1.0, 1.25, 1.5):
        pixels_per_day = base_pixels_per_day * zoom
        assert layer.setProperty("pixelsPerDay", pixels_per_day)
        _process_events(application)
        by_type = {route["dependencyType"]: route for route in _routes(layer)}

        predecessor_start = pixels_per_day
        predecessor_finish = predecessor_start + max(12.0, 2.0 * pixels_per_day)
        successor_start = 5.0 * pixels_per_day
        successor_finish = successor_start + max(12.0, 3.0 * pixels_per_day)
        assert by_type["FS"]["sourceX"] == pytest.approx(predecessor_finish)
        assert by_type["FS"]["targetX"] == pytest.approx(successor_start)
        assert by_type["SS"]["sourceX"] == pytest.approx(predecessor_start)
        assert by_type["SS"]["targetX"] == pytest.approx(successor_start)
        assert by_type["FF"]["sourceX"] == pytest.approx(predecessor_finish)
        assert by_type["FF"]["targetX"] == pytest.approx(successor_finish)
        assert by_type["SF"]["sourceX"] == pytest.approx(predecessor_start)
        assert by_type["SF"]["targetX"] == pytest.approx(successor_finish)

        routes_before_scroll = _routes(layer)
        assert layer.setProperty("timelineContentX", pixels_per_day * 0.5)
        _process_events(application)
        assert _routes(layer) == routes_before_scroll, (timescale, zoom)

    layer.deleteLater()
    _process_events(application)


@pytest.mark.parametrize("requested_dpr", (1.0, 1.25, 1.5, 2.0))
def test_canvas_painted_output_tracks_scroll_and_row_centers_at_supported_dpr(
    requested_dpr: float,
) -> None:
    probe_code = (
        "import json; "
        "from src.tests.project_management.test_r4_5e_gantt_dependencies "
        "import _canvas_paint_probe; "
        "print('R45E_PROBE=' + json.dumps(_canvas_paint_probe()))"
    )
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["QT_SCALE_FACTOR"] = str(requested_dpr)
    completed = subprocess.run(
        [sys.executable, "-c", probe_code],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload_line = next(
        line for line in completed.stdout.splitlines() if line.startswith("R45E_PROBE=")
    )
    payload = json.loads(payload_line.removeprefix("R45E_PROBE="))
    assert payload["devicePixelRatio"] == pytest.approx(requested_dpr, abs=0.01)
    assert payload["pixelScale"] == pytest.approx(requested_dpr, abs=0.01)
    assert all(payload["endpointAlignment"].values())
    assert payload["fullyOffscreenClipped"] is True
    assert payload["sourceX"] == pytest.approx(144.0)
    assert payload["targetX"] == pytest.approx(168.0)

    def logical_bounds(name: str) -> list[float]:
        scale = payload["pixelScale"]
        return [value / scale for value in payload[name][:4]]

    initial = logical_bounds("initial")
    horizontal = logical_bounds("horizontal")
    vertical = logical_bounds("vertical")
    generalized_origin = logical_bounds("generalizedOrigin")
    tolerance = max(0.8, 1.0 / payload["pixelScale"])

    assert horizontal[0] == pytest.approx(initial[0] - 100.0, abs=tolerance)
    assert horizontal[2] == pytest.approx(initial[2] - 100.0, abs=tolerance)
    assert horizontal[1] == pytest.approx(initial[1], abs=tolerance)
    assert horizontal[3] == pytest.approx(initial[3], abs=tolerance)
    assert vertical[0] == pytest.approx(horizontal[0], abs=tolerance)
    assert vertical[2] == pytest.approx(horizontal[2], abs=tolerance)
    assert vertical[1] == pytest.approx(horizontal[1] - 12.0, abs=tolerance)
    assert vertical[3] == pytest.approx(horizontal[3] - 12.0, abs=tolerance)
    assert generalized_origin == pytest.approx(vertical, abs=tolerance)


@pytest.mark.parametrize(
    ("predecessor_index", "successor_index"),
    ((0, 1), (5, 6), (10, 11)),
)
def test_canvas_paints_first_middle_and_last_row_endpoints_at_exact_centers(
    predecessor_index: int,
    successor_index: int,
) -> None:
    projection = _long_chain_projection(12)
    model = GanttListModel()
    model.set_projection(replace(projection, dependency_edges=()))
    predecessor_id = model.taskIdAt(predecessor_index)
    successor_id = model.taskIdAt(successor_index)
    rows_by_id = {row.task_id: row for row in projection.rows}
    edge = replace(
        projection.dependency_edges[0],
        predecessor_task_id=predecessor_id,
        predecessor_task_name=rows_by_id[predecessor_id].name,
        successor_task_id=successor_id,
        successor_task_name=rows_by_id[successor_id].name,
    )
    model.set_projection(replace(projection, dependency_edges=(edge,)))
    application, _engine, view, layer = _create_layer(
        model,
        connector_color=QColor("#ff0000"),
    )
    view.setColor(QColor("#ffffff"))
    view.resize(300, 450)
    _process_events(application)
    QTest.qWait(40)

    route = _routes(layer)[0]
    expected_source_y = (predecessor_index + 0.5) * 36.0
    expected_target_y = (successor_index + 0.5) * 36.0
    assert route["sourceY"] == pytest.approx(expected_source_y)
    assert route["targetY"] == pytest.approx(expected_target_y)
    image = view.grabWindow()
    pixel_scale = float(image.width()) / float(view.width())
    assert _has_red_near(
        image, float(route["sourceX"]), expected_source_y, pixel_scale
    )
    assert _has_red_near(
        image, float(route["targetX"]), expected_target_y, pixel_scale
    )

    view.close()
    layer.deleteLater()
    _process_events(application)


def test_continuous_scroll_repaints_without_route_rebuild_or_material_regression() -> None:
    class CountingModel(GanttListModel):
        def __init__(self) -> None:
            super().__init__()
            self.window_calls = 0

        def dependencyWindow(self, *args):
            self.window_calls += 1
            return super().dependencyWindow(*args)

    model = CountingModel()
    model.set_projection(_typed_projection())
    application, _engine, _view, layer = _create_layer(model)
    initial_routes = _routes(layer)
    initial_window_calls = model.window_calls

    started = perf_counter()
    for frame in range(120):
        assert layer.setProperty("timelineContentX", float(frame))
        assert layer.setProperty("verticalContentY", float(frame % 18))
        _process_events(application, passes=1)
    elapsed_ms = (perf_counter() - started) * 1_000

    assert _routes(layer) == initial_routes
    assert model.window_calls == initial_window_calls
    assert elapsed_ms < 1_000
    print(f"R4.5E continuous scroll frames=120 elapsed_ms={elapsed_ms:.3f}")
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
    assert "devicePixelRatio" not in layer
    assert "canvasSize:" not in layer
    assert "context.scale(" not in layer
    assert "onTimelineContentXChanged: dependencyCanvas.requestPaint()" in layer
    assert "onVerticalContentYChanged: dependencyCanvas.requestPaint()" in layer
    assert "route.sourceX - root.timelineContentX" in layer
    assert "route.sourceY - root.rowScrollOffset" in layer
    assert "root.verticalContentY - root.verticalOriginY" in layer
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
