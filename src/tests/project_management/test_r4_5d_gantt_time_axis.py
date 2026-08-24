from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from time import perf_counter

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlExpression

from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.gantt_builder import (
    build_gantt_projection,
)
from src.tests.path_rewrites import REPO_ROOT
from src.tests.project_management.test_r4_5b_gantt_read_contract import (
    _CountingEngine,
    _ScopeContext,
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
    return existing or QGuiApplication(["r4-5d-gantt-test"])


def _dated_projection(
    start: date | None,
    finish: date | None,
    *,
    actual_start: date | None = None,
    actual_finish: date | None = None,
    project_start: date | None = None,
    project_finish: date | None = None,
    work_calendar: object | None = None,
):
    task = _task("task-1", code="TASK-001", wbs="1")
    task.actual_start = actual_start
    task.actual_end = actual_finish
    return build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=(_node(task),),
        schedule_items=(_schedule(task, start=start, finish=finish),),
        project_start=project_start,
        project_finish=project_finish,
        work_calendar=work_calendar,
    )


def _empty_projection():
    return build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=(),
        schedule_items=(),
    )


def _interval_contains(intervals: tuple[object, ...], value: date) -> bool:
    ordinal = value.toordinal()
    return any(
        interval.start_day_ordinal <= ordinal <= interval.finish_day_ordinal
        for interval in intervals
    )


def test_projection_range_includes_planned_actual_and_project_bounds_without_clipping() -> None:
    projection = _dated_projection(
        date(2026, 2, 1),
        date(2026, 2, 10),
        actual_start=date(2026, 1, 20),
        actual_finish=date(2026, 3, 8),
        project_start=date(2026, 1, 25),
        project_finish=date(2026, 3, 1),
    )

    assert projection.project_start_day_ordinal == date(2026, 1, 25).toordinal()
    assert projection.project_finish_day_ordinal == date(2026, 3, 1).toordinal()
    assert projection.range_start_day_ordinal == date(2026, 1, 20).toordinal()
    assert projection.range_finish_day_ordinal == date(2026, 3, 8).toordinal()


def test_projection_no_date_and_same_day_ranges_are_truthful() -> None:
    empty = _empty_projection()
    assert empty.range_start_day_ordinal is None
    assert empty.range_finish_day_ordinal is None

    one_day = _dated_projection(date(2026, 6, 4), date(2026, 6, 4))
    assert one_day.range_start_day_ordinal == date(2026, 6, 4).toordinal()
    assert one_day.range_finish_day_ordinal == date(2026, 6, 4).toordinal()


def test_calendar_shading_uses_authoritative_working_dates_and_exceptions() -> None:
    holiday = date(2026, 6, 3)

    class Calendar:
        @staticmethod
        def working_day_dates_between(start: date, finish: date) -> tuple[date, ...]:
            values: list[date] = []
            cursor = start
            while cursor <= finish:
                # Saturday is deliberately working; Sunday and one weekday are not.
                if cursor.weekday() != 6 and cursor != holiday:
                    values.append(cursor)
                cursor += timedelta(days=1)
            return tuple(values)

    projection = _dated_projection(
        date(2026, 6, 1),
        date(2026, 6, 8),
        work_calendar=Calendar(),
    )

    assert projection.calendar_shading_authoritative is True
    assert _interval_contains(projection.non_working_intervals, holiday)
    assert _interval_contains(projection.non_working_intervals, date(2026, 6, 7))
    assert not _interval_contains(projection.non_working_intervals, date(2026, 6, 6))

    no_calendar = _dated_projection(date(2026, 6, 1), date(2026, 6, 8))
    assert no_calendar.calendar_shading_authoritative is False
    assert no_calendar.non_working_intervals == ()


def test_desktop_api_projects_project_bounds_and_bound_calendar() -> None:
    task = _task("task-1", code="TASK-001", wbs="1")
    engine = _CountingEngine(task)
    calendar_calls: list[str] = []

    class Calendar:
        @staticmethod
        def working_day_dates_between(start: date, finish: date) -> tuple[date, ...]:
            values: list[date] = []
            cursor = start
            while cursor <= finish:
                if cursor.weekday() < 5:
                    values.append(cursor)
                cursor += timedelta(days=1)
            return tuple(values)

    calendar = Calendar()

    def calendar_for_project(project_id: str) -> Calendar:
        calendar_calls.append(project_id)
        return calendar

    engine.calendar_for_project = calendar_for_project
    project = type(
        "Project",
        (),
        {
            "id": "project-1",
            "tenant_id": "tenant-1",
            "organization_id": "org-1",
            "start_date": date(2025, 12, 1),
            "end_date": date(2026, 2, 1),
        },
    )()
    task_service = type(
        "TaskService",
        (),
        {
            "list_task_hierarchy": lambda _self, _project_id: [_node(task)],
            "list_dependencies_for_project": lambda _self, _project_id: [],
        },
    )()
    api = ProjectManagementSchedulingDesktopApi(
        project_service=type(
            "ProjectService",
            (),
            {"get_project": lambda _self, _project_id: project},
        )(),
        task_service=task_service,
        scheduling_engine=engine,
        tenant_context_service=_ScopeContext("tenant-1", "org-1"),
    )

    projection = api.build_gantt_projection("project-1")

    assert calendar_calls == ["project-1"]
    assert projection.project_start_day_ordinal == date(2025, 12, 1).toordinal()
    assert projection.project_finish_day_ordinal == date(2026, 2, 1).toordinal()
    assert projection.range_start_day_ordinal == date(2025, 12, 1).toordinal()
    assert projection.range_finish_day_ordinal == date(2026, 2, 1).toordinal()
    assert projection.calendar_shading_authoritative is True


@pytest.mark.parametrize(
    ("timescale", "expected_start", "expected_finish", "density"),
    (
        ("day", date(2026, 1, 28), date(2026, 2, 13), 40.0),
        ("week", date(2026, 1, 24), date(2026, 2, 17), 12.0),
        ("month", date(2025, 12, 31), date(2026, 3, 10), 4.0),
        ("quarter", date(2025, 10, 31), date(2026, 5, 10), 1.5),
    ),
)
def test_axis_applies_exact_scale_padding_and_base_density(
    timescale: str,
    expected_start: date,
    expected_finish: date,
    density: float,
) -> None:
    axis = GanttTimeAxisController(today_provider=lambda: date(2026, 2, 5))
    axis.set_projection(_dated_projection(date(2026, 1, 31), date(2026, 2, 10)))

    assert axis.setTimescale(timescale) is True
    assert axis.rangeStartDay == expected_start.toordinal()
    assert axis.rangeFinishDay == expected_finish.toordinal()
    assert axis.pixelsPerDay == density
    assert axis.contentWidth == pytest.approx(axis.rangeDayCount * density)


def test_axis_defaults_to_week_and_has_discrete_resetting_zoom() -> None:
    axis = GanttTimeAxisController()
    axis.set_projection(_dated_projection(date(2026, 1, 1), date(2026, 2, 1)))

    assert axis.timescale == "week"
    assert axis.zoomLevels == [0.75, 0.875, 1.0, 1.25, 1.5]
    assert axis.zoomIndex == 2
    assert axis.zoomIn() is True
    assert axis.zoomMultiplier == 1.25
    assert axis.pixelsPerDay == 15.0
    assert axis.zoomIn() is True
    assert axis.zoomIn() is False
    assert axis.canZoomIn is False
    assert axis.resetZoom() is True
    assert axis.zoomMultiplier == 1.0
    assert axis.zoomOut() is True
    assert axis.setTimescale("month") is True
    assert axis.zoomIndex == 2
    assert axis.setTimescale("invalid") is False
    assert axis.timescale == "month"


@pytest.mark.parametrize(
    ("timescale", "expected_major_label", "expected_minor_label"),
    (
        ("day", "February 2020", "29"),
        ("week", "January 2020", "W01"),
        ("month", "2020", "Feb"),
        ("quarter", "2020", "Q1"),
    ),
)
def test_two_band_ticks_follow_calendar_boundaries(
    timescale: str,
    expected_major_label: str,
    expected_minor_label: str,
) -> None:
    axis = GanttTimeAxisController()
    axis.set_projection(_dated_projection(date(2019, 12, 29), date(2020, 3, 3)))
    axis.setTimescale(timescale)
    axis.updateViewport(0, min(axis.contentWidth, 8_000))

    assert axis.majorTicks
    assert axis.minorTicks
    assert {tick["kind"] for tick in axis.majorTicks} == {"major"}
    assert {tick["kind"] for tick in axis.minorTicks} == {"minor"}
    assert expected_major_label in {tick["label"] for tick in axis.majorTicks}
    assert expected_minor_label in {tick["label"] for tick in axis.minorTicks}
    if timescale == "day":
        assert any(
            tick["startDay"] == date(2020, 2, 29).toordinal()
            for tick in axis.minorTicks
        )
    if timescale == "week":
        iso_boundary = next(
            tick
            for tick in axis.minorTicks
            if tick["startDay"] == date(2019, 12, 30).toordinal()
        )
        assert iso_boundary["label"] == "W01"
    if timescale == "quarter":
        assert {tick["label"] for tick in axis.minorTicks} >= {"Q1"}


def test_today_never_expands_range_and_is_disabled_outside_it() -> None:
    outside_axis = GanttTimeAxisController(today_provider=lambda: date(2030, 1, 1))
    outside_axis.set_projection(_dated_projection(date(2026, 1, 1), date(2026, 1, 2)))
    original_range = (outside_axis.rangeStartDay, outside_axis.rangeFinishDay)

    assert outside_axis.todayAvailable is False
    assert outside_axis.todayUnavailableReason == "Today is outside this schedule."
    assert (outside_axis.rangeStartDay, outside_axis.rangeFinishDay) == original_range

    inside_axis = GanttTimeAxisController(today_provider=lambda: date(2026, 1, 1))
    inside_axis.set_projection(_dated_projection(date(2026, 1, 1), date(2026, 1, 2)))
    assert inside_axis.todayAvailable is True
    assert inside_axis.todayUnavailableReason == ""

    no_date_axis = GanttTimeAxisController()
    no_date_axis.set_projection(_empty_projection())
    assert no_date_axis.hasRange is False
    assert no_date_axis.contentWidth == 0
    assert no_date_axis.todayAvailable is False
    assert no_date_axis.todayUnavailableReason == "No scheduled date range is available."


def test_axis_range_is_stable_across_filter_sort_and_hierarchy_state() -> None:
    projection = _projection(20)
    model = GanttListModel()
    axis = GanttTimeAxisController()
    model.set_projection(projection)
    axis.set_projection(projection)
    original = (axis.baseRangeStartDay, axis.baseRangeFinishDay, axis.rangeStartDay, axis.rangeFinishDay)

    model.apply_view(
        search_text="Task 19",
        status_filter="all",
        critical_only=False,
        delayed_only=False,
        sort_key="taskName",
        sort_descending=True,
    )
    model.set_expanded("task-0", False)

    assert (axis.baseRangeStartDay, axis.baseRangeFinishDay, axis.rangeStartDay, axis.rangeFinishDay) == original


def test_bar_geometry_uses_one_inclusive_day_formula() -> None:
    application = _application()
    engine = create_qml_engine()
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str(GANTT_ROOT / "SchedulingGanttBar.qml")),
    )
    bar = component.create()
    assert bar is not None, "\n".join(error.toString() for error in component.errors())

    axis_start = date(2026, 1, 1).toordinal()
    assert bar.setProperty("axisStartDay", axis_start)
    assert bar.setProperty("startDay", axis_start + 2)
    assert bar.setProperty("finishDay", axis_start + 4)
    assert bar.setProperty("pixelsPerDay", 10.0)
    assert bar.setProperty("progressPercent", 50.0)
    application.processEvents()

    assert bar.property("contentStartX") == pytest.approx(20.0)
    assert bar.property("taskWidth") == pytest.approx(30.0)
    assert bar.property("progressWidth") == pytest.approx(15.0)
    assert bar.property("x") == pytest.approx(20.0)

    assert bar.setProperty("finishDay", axis_start + 2)
    assert bar.setProperty("isMilestone", True)
    application.processEvents()
    assert bar.property("contentCenterX") == pytest.approx(25.0)
    assert bar.property("x") == pytest.approx(18.0)
    assert bar.property("width") == pytest.approx(14.0)

    assert bar.setProperty("startDay", -1)
    assert bar.setProperty("finishDay", -1)
    application.processEvents()
    assert bar.property("visible") is False
    bar.deleteLater()
    application.processEvents()


def test_surface_preserves_center_across_zoom_timescale_and_resize() -> None:
    application = _application()
    engine = create_qml_engine()
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str(GANTT_ROOT / "SchedulingGanttSurface.qml")),
    )
    surface = component.create()
    assert surface is not None, "\n".join(error.toString() for error in component.errors())
    axis = GanttTimeAxisController(today_provider=lambda: date(2026, 6, 1))
    axis.set_projection(_dated_projection(date(2026, 1, 1), date(2026, 12, 31)))

    assert surface.setProperty("width", 1280)
    assert surface.setProperty("height", 640)
    assert surface.setProperty("requestedViewMode", "timeline")
    assert surface.setProperty("axisModel", axis)
    application.processEvents()
    application.processEvents()
    timeline = surface.findChild(QObject, "ganttTimelineHorizontalAuthority")
    assert timeline is not None
    assert timeline.setProperty("contentX", 1_500.0)
    application.processEvents()

    def center_day() -> float:
        return axis.rangeStartDay + (
            float(timeline.property("contentX")) + float(timeline.property("width")) / 2
        ) / axis.pixelsPerDay

    before = center_day()
    expression = QQmlExpression(engine.rootContext(), surface, "zoomIn()")
    value, is_undefined = expression.evaluate()
    assert value is True and is_undefined is False
    application.processEvents()
    application.processEvents()
    assert center_day() == pytest.approx(before, abs=1.0)

    expression = QQmlExpression(engine.rootContext(), surface, "setTimescale('month')")
    value, is_undefined = expression.evaluate()
    assert value is True and is_undefined is False
    application.processEvents()
    application.processEvents()
    assert center_day() == pytest.approx(before, abs=1.0)

    assert surface.setProperty("width", 1440)
    application.processEvents()
    application.processEvents()
    assert center_day() == pytest.approx(before, abs=1.0)
    surface.deleteLater()
    application.processEvents()


def test_axis_interactions_do_not_refresh_or_run_cpm_and_qml_has_one_authority() -> None:
    projection = _dated_projection(date(2026, 1, 1), date(2026, 12, 31))
    controller = ProjectManagementSchedulingWorkspaceController()
    controller._gantt_model.set_projection(projection)
    controller._gantt_time_axis.set_projection(projection)
    controller.refresh = lambda: (_ for _ in ()).throw(
        AssertionError("Display-only axis interaction must not refresh or run CPM")
    )

    controller.ganttTimeAxis.zoomIn()
    controller.ganttTimeAxis.setTimescale("month")
    controller.ganttTimeAxis.updateViewport(200, 900)
    controller.selectActivity("task-1")

    surface = (GANTT_ROOT / "SchedulingGanttSurface.qml").read_text(encoding="utf-8")
    header = (GANTT_ROOT / "SchedulingGanttHeader.qml").read_text(encoding="utf-8")
    row = (GANTT_ROOT / "SchedulingGanttRow.qml").read_text(encoding="utf-8")
    assert surface.count('objectName: "ganttTimelineHorizontalAuthority"') == 1
    assert surface.count('objectName: "ganttTodayMarker"') == 1
    assert "Flickable" not in header
    assert "todayMarker" not in row
    assert "refresh()" not in surface


@pytest.mark.parametrize("row_count", [100, 1_000, 5_000])
def test_axis_interactions_are_bounded_for_large_projects(row_count: int) -> None:
    projection = _projection(row_count)
    axis = GanttTimeAxisController()
    started = perf_counter()
    axis.set_projection(projection)
    axis.setTimescale("day")
    axis.updateViewport(max(0, axis.contentWidth / 2), 1_280)
    axis.zoomIn()
    axis.zoomOut()
    elapsed_ms = (perf_counter() - started) * 1_000

    print(
        f"R4.5D axis rows={row_count} elapsed_ms={elapsed_ms:.3f} "
        f"major_ticks={len(axis.majorTicks)} minor_ticks={len(axis.minorTicks)}"
    )
    assert elapsed_ms < 100
    assert len(axis.majorTicks) < 10
    assert len(axis.minorTicks) < 100


def test_multi_year_axis_generates_only_visible_buffered_ticks() -> None:
    axis = GanttTimeAxisController()
    axis.set_projection(_dated_projection(date(1000, 1, 1), date(5000, 12, 31)))

    started = perf_counter()
    axis.setTimescale("day")
    axis.updateViewport(axis.contentWidth / 2, 1_280)
    elapsed_ms = (perf_counter() - started) * 1_000

    assert elapsed_ms < 100
    assert len(axis.majorTicks) < 10
    assert len(axis.minorTicks) < 100
    assert axis.rangeWarning
