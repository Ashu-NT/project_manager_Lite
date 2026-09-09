from __future__ import annotations

import os
from dataclasses import replace
from datetime import date
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent

from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.gantt_builder import (
    build_gantt_baseline_overlay,
    build_gantt_projection,
)
from src.core.modules.project_management.domain.scheduling.baseline import BaselineTask
from src.core.platform.common.exceptions import NotFoundError
from src.tests.path_rewrites import REPO_ROOT
from src.tests.project_management.test_r4_5b_gantt_read_contract import (
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


def _baseline_task(
    task_id: str,
    *,
    start: date | None = date(2025, 12, 20),
    finish: date | None = date(2025, 12, 22),
    milestone: bool = False,
) -> BaselineTask:
    return BaselineTask.create(
        baseline_id="baseline-1",
        task_id=task_id,
        task_name=task_id,
        baseline_start=start,
        baseline_finish=finish,
        baseline_duration_days=0 if milestone else 3,
        baseline_planned_cost=0,
        baseline_is_milestone=milestone,
    )


def _overlay(*tasks: BaselineTask, project_id: str = "project-1"):
    return build_gantt_baseline_overlay(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id=project_id,
        baseline_id="baseline-1",
        baseline_tasks=tasks,
    )


class _CountingBaselineReader:
    def __init__(self, rows: tuple[BaselineTask, ...]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, str | None]] = []

    def list_baseline_tasks(self, baseline_id: str, *, expected_project_id=None):
        self.calls.append((baseline_id, expected_project_id))
        return list(self.rows)


def _project(*, organization_id: str = "org-1") -> SimpleNamespace:
    return SimpleNamespace(
        id="project-1",
        tenant_id="tenant-1",
        organization_id=organization_id,
    )


def test_overlay_api_uses_one_authorized_bulk_read_and_never_calls_cpm() -> None:
    reader = _CountingBaselineReader((_baseline_task("task-1"),))
    engine = SimpleNamespace(
        recalculate_project_schedule=lambda *_args, **_kwargs: pytest.fail(
            "Baseline display selection must not run CPM."
        )
    )
    api = ProjectManagementSchedulingDesktopApi(
        project_service=SimpleNamespace(get_project=lambda _id: _project()),
        scheduling_engine=engine,
        baseline_service=reader,
        tenant_context_service=_ScopeContext("tenant-1", "org-1"),
    )

    overlay = api.build_gantt_baseline_overlay("project-1", "baseline-1")

    assert reader.calls == [("baseline-1", "project-1")]
    assert overlay.project_id == "project-1"
    assert overlay.baseline_id == "baseline-1"
    assert [row.task_id for row in overlay.snapshots] == ["task-1"]


def test_overlay_api_rejects_cross_organization_before_snapshot_read() -> None:
    reader = _CountingBaselineReader((_baseline_task("task-1"),))
    api = ProjectManagementSchedulingDesktopApi(
        project_service=SimpleNamespace(get_project=lambda _id: _project()),
        baseline_service=reader,
        tenant_context_service=_ScopeContext("tenant-1", "org-2"),
    )

    with pytest.raises(NotFoundError):
        api.build_gantt_baseline_overlay("project-1", "baseline-1")
    assert reader.calls == []


def test_overlay_api_propagates_authorization_denial_without_returning_snapshots() -> None:
    class DeniedReader:
        def list_baseline_tasks(self, *_args, **_kwargs):
            raise PermissionError("denied")

    api = ProjectManagementSchedulingDesktopApi(
        project_service=SimpleNamespace(get_project=lambda _id: _project()),
        baseline_service=DeniedReader(),
        tenant_context_service=_ScopeContext("tenant-1", "org-1"),
    )

    with pytest.raises(PermissionError, match="denied"):
        api.build_gantt_baseline_overlay("project-1", "baseline-1")


def test_model_indexes_matching_rows_omits_summary_overlay_and_counts_orphans() -> None:
    model = GanttListModel()
    model.set_projection(_projection(2))
    model.set_baseline_overlay(
        _overlay(
            _baseline_task("task-0", milestone=True),
            _baseline_task("historical-only"),
        )
    )

    assert model.selectedBaselineId == "baseline-1"
    assert model.baselineTaskCount == 2
    assert model.baselineMatchedTaskCount == 1
    assert model.baselineOrphanTaskCount == 1
    assert model.baseline_for_task("task-0").baseline_is_milestone is True
    baseline_role = model.data(model.index(0, 0), model.BaselineDataRole)
    assert baseline_role["isMilestone"] is True
    assert baseline_role["startDayOrdinal"] == date(2025, 12, 20).toordinal()

    model.set_baseline_overlay(None)
    assert model.baselineTaskCount == 0
    assert model.data(model.index(0, 0), model.BaselineDataRole) == {}


def test_model_rejects_cross_tenant_or_organization_overlay() -> None:
    model = GanttListModel()
    model.set_projection(_projection(1))
    overlay = _overlay(_baseline_task("task-0"))

    with pytest.raises(ValueError, match="another scope"):
        model.set_baseline_overlay(replace(overlay, organization_id="org-2"))
    with pytest.raises(ValueError, match="another scope"):
        model.set_baseline_overlay(replace(overlay, tenant_id="tenant-2"))
    assert model.baselineTaskCount == 0


def test_missing_and_unscheduled_combinations_do_not_fabricate_rows_or_geometry() -> None:
    task = _task("task-1", code="TASK-1", wbs="1")
    projection = build_gantt_projection(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        hierarchy_nodes=(_node(task),),
        schedule_items=(_schedule(task, start=None, finish=None),),
    )
    model = GanttListModel()
    axis = GanttTimeAxisController()
    model.set_projection(projection)
    axis.set_projection(projection)

    assert model.data(model.index(0, 0), model.BaselineDataRole) == {}
    assert axis.hasRange is False

    overlay = _overlay(
        _baseline_task("task-1"),
        _baseline_task("historical-only"),
    )
    model.set_baseline_overlay(overlay)
    axis.set_baseline_overlay(overlay)

    assert model.rowCountValue == 1
    assert model.baselineOrphanTaskCount == 1
    assert model.data(model.index(0, 0), model.RowDataRole)["startDate"] == ""
    assert model.data(model.index(0, 0), model.BaselineDataRole)["startDate"]
    assert axis.hasRange is True

    unscheduled_baseline = _overlay(
        _baseline_task("task-1", start=None, finish=None)
    )
    model.set_baseline_overlay(unscheduled_baseline)
    baseline_data = model.data(model.index(0, 0), model.BaselineDataRole)
    assert baseline_data["startDayOrdinal"] is None
    assert baseline_data["finishDayOrdinal"] is None


@pytest.mark.parametrize(
    ("baseline_start", "baseline_finish", "expected_start", "expected_finish"),
    [
        (date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 1), date(2026, 1, 2)),
        (date(2025, 12, 1), date(2026, 1, 1), date(2025, 12, 1), date(2026, 1, 2)),
        (date(2026, 1, 2), date(2026, 2, 1), date(2026, 1, 1), date(2026, 2, 1)),
        (date(2025, 12, 1), date(2026, 2, 1), date(2025, 12, 1), date(2026, 2, 1)),
    ],
)
def test_axis_adds_and_removes_only_selected_baseline_bounds(
    baseline_start: date,
    baseline_finish: date,
    expected_start: date,
    expected_finish: date,
) -> None:
    projection = _projection(1)
    axis = GanttTimeAxisController()
    axis.set_projection(projection)
    original = (axis.baseRangeStartDay, axis.baseRangeFinishDay)

    axis.set_baseline_overlay(
        _overlay(
            _baseline_task(
                "task-0",
                start=baseline_start,
                finish=baseline_finish,
            )
        )
    )
    assert axis.baseRangeStartDay == expected_start.toordinal()
    assert axis.baseRangeFinishDay == expected_finish.toordinal()

    axis.set_baseline_overlay(None)
    assert (axis.baseRangeStartDay, axis.baseRangeFinishDay) == original


def test_controller_baseline_selection_is_local_retry_safe_and_none_is_free() -> None:
    controller = ProjectManagementSchedulingWorkspaceController()
    projection = _projection(1)
    controller._gantt_model.set_projection(projection)
    controller._gantt_time_axis.set_projection(projection)
    controller._selected_project_id = "project-1"
    controller._baseline_options = [{"value": "baseline-1", "label": "Baseline One"}]
    calls: list[tuple[str, str]] = []

    class Presenter:
        def build_gantt_baseline_overlay(self, project_id: str, baseline_id: str):
            calls.append((project_id, baseline_id))
            return _overlay(_baseline_task("task-0", milestone=True))

    controller._scheduling_workspace_presenter = Presenter()
    controller.refresh = lambda: pytest.fail("Gantt baseline selection must stay local.")

    controller.selectGanttBaseline("baseline-1")
    assert calls == [("project-1", "baseline-1")]
    assert controller.ganttSelectedBaselineId == "baseline-1"
    assert controller.ganttBaselineError == ""
    assert controller.ganttRowsModel.baselineTaskCount == 1

    controller.selectGanttBaseline("")
    assert calls == [("project-1", "baseline-1")]
    assert controller.ganttSelectedBaselineId == ""
    assert controller.ganttRowsModel.baselineTaskCount == 0


def test_failed_overlay_never_leaves_stale_geometry_and_can_retry() -> None:
    controller = ProjectManagementSchedulingWorkspaceController()
    projection = _projection(1)
    controller._gantt_model.set_projection(projection)
    controller._gantt_time_axis.set_projection(projection)
    controller._selected_project_id = "project-1"
    controller._baseline_options = [{"value": "baseline-1", "label": "Baseline One"}]
    overlay = _overlay(_baseline_task("task-0"))
    controller._gantt_model.set_baseline_overlay(overlay)
    controller._gantt_time_axis.set_baseline_overlay(overlay)

    class Presenter:
        def build_gantt_baseline_overlay(self, *_args):
            raise RuntimeError("sensitive repository detail")

    controller._scheduling_workspace_presenter = Presenter()
    controller._gantt_selected_baseline_id = "baseline-1"
    controller._gantt_baseline_error = "retry"
    controller.retryGanttBaseline()

    assert controller.ganttRowsModel.baselineTaskCount == 0
    assert controller.ganttBaselineError == (
        "Baseline comparison could not be loaded. Retry or choose None."
    )
    assert "sensitive" not in controller.ganttBaselineError


def test_project_switch_clears_local_baseline_and_current_selection() -> None:
    controller = ProjectManagementSchedulingWorkspaceController()
    projection = _projection(1)
    overlay = _overlay(_baseline_task("task-0"))
    controller._selected_project_id = "project-1"
    controller._gantt_selected_baseline_id = "baseline-1"
    controller._gantt_model.set_projection(projection)
    controller._gantt_time_axis.set_projection(projection)
    controller._gantt_model.set_baseline_overlay(overlay)
    controller._gantt_time_axis.set_baseline_overlay(overlay)
    controller.refresh = lambda: None

    controller.selectProject("project-2")

    assert controller.ganttSelectedBaselineId == ""
    assert controller.ganttRowsModel.baselineTaskCount == 0
    assert controller.ganttTimeAxis.baseRangeStartDay == projection.range_start_day_ordinal


def _application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    return existing or QGuiApplication(["r4-5f-gantt-test"])


def _create_component(name: str):
    application = _application()
    engine = create_qml_engine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(GANTT_ROOT / name)))
    item = component.create()
    assert item is not None, "\n".join(error.toString() for error in component.errors())
    return application, engine, component, item


def test_current_milestone_and_same_day_task_use_explicit_fact_only() -> None:
    application, _engine, _component, bar = _create_component("SchedulingGanttBar.qml")
    for name, value in {
        "axisStartDay": date(2026, 1, 1).toordinal(),
        "startDay": date(2026, 1, 2).toordinal(),
        "finishDay": date(2026, 1, 2).toordinal(),
        "pixelsPerDay": 2.0,
    }.items():
        assert bar.setProperty(name, value)
    application.processEvents()
    shape = bar.findChild(QObject, "currentGanttShape")
    assert shape is not None
    assert float(bar.property("width")) == 12
    assert float(shape.property("rotation")) == 0

    assert bar.setProperty("isMilestone", True)
    application.processEvents()
    assert float(shape.property("rotation")) == 45
    assert float(bar.property("progressWidth")) == 0
    bar.deleteLater()


def test_baseline_milestone_and_semantic_precedence_are_truthful() -> None:
    application, _engine, _component, baseline = _create_component(
        "SchedulingGanttBaseline.qml"
    )
    for name, value in {
        "axisStartDay": date(2026, 1, 1).toordinal(),
        "startDay": date(2026, 1, 2).toordinal(),
        "finishDay": date(2026, 1, 2).toordinal(),
        "pixelsPerDay": 2.0,
        "isMilestone": True,
    }.items():
        assert baseline.setProperty(name, value)
    application.processEvents()
    baseline_shape = baseline.findChild(QObject, "baselineGanttShape")
    assert baseline_shape is not None
    assert float(baseline_shape.property("rotation")) == 45
    assert float(baseline.property("width")) == 9
    assert baseline.setProperty("isMilestone", False)
    application.processEvents()
    assert float(baseline_shape.property("rotation")) == 0
    assert float(baseline.property("width")) == 8
    baseline.deleteLater()

    _application, _engine, _component, bar = _create_component(
        "SchedulingGanttBar.qml"
    )
    normal = bar.property("semanticColor")
    assert bar.setProperty("isCritical", True)
    application.processEvents()
    critical = bar.property("semanticColor")
    assert critical != normal
    assert bar.setProperty("highlightCriticalTasks", False)
    application.processEvents()
    assert bar.property("semanticColor") == normal
    assert bar.setProperty("isInfeasible", True)
    application.processEvents()
    infeasible = bar.property("semanticColor")
    assert infeasible != normal and infeasible != critical
    assert bar.setProperty("selected", True)
    application.processEvents()
    assert int(bar.property("selectionOutlineWidth")) == 2
    assert bar.property("semanticColor") == infeasible
    bar.deleteLater()


@pytest.mark.parametrize("row_count", [100, 1_000, 5_000])
def test_baseline_index_and_display_lookup_remain_linear(row_count: int) -> None:
    projection = _projection(row_count)
    rows = tuple(_baseline_task(f"task-{index}") for index in range(row_count))
    build_started = perf_counter()
    overlay = _overlay(*rows)
    build_ms = (perf_counter() - build_started) * 1_000
    model = GanttListModel()
    model.set_projection(projection)
    index_started = perf_counter()
    model.set_baseline_overlay(overlay)
    index_ms = (perf_counter() - index_started) * 1_000
    lookup_started = perf_counter()
    for index in range(min(row_count, 30)):
        assert model.baseline_for_task(f"task-{index}") is not None
    lookup_ms = (perf_counter() - lookup_started) * 1_000
    print(
        f"R4.5F baseline rows={row_count} build_ms={build_ms:.3f} "
        f"index_ms={index_ms:.3f} visible_lookup_ms={lookup_ms:.3f}"
    )
    assert model.baselineTaskCount == row_count
    assert model.baselineOrphanTaskCount == 0
    assert build_ms < 3_000
    assert index_ms < 3_000
    assert lookup_ms < 50


def test_qml_architecture_uses_one_overlay_per_recycled_row_and_no_fake_critical_edges() -> None:
    panel = (GANTT_ROOT.parent.parent / "panels" / "SchedulingGanttPanel.qml").read_text(
        encoding="utf-8"
    )
    row = (GANTT_ROOT / "SchedulingGanttRow.qml").read_text(encoding="utf-8")
    dependency = (GANTT_ROOT / "SchedulingGanttDependencyLayer.qml").read_text(
        encoding="utf-8"
    )
    bar = (GANTT_ROOT / "SchedulingGanttBar.qml").read_text(encoding="utf-8")

    assert 'text: "Highlight Critical Tasks"' in panel
    assert '"value": "", "label": "None"' in panel
    assert row.count("SchedulingGanttBaseline {") == 1
    assert "Repeater" not in row.split("SchedulingGanttBaseline {")[1]
    assert "totalFloat" not in bar
    assert "criticalPath" not in dependency
    assert "criticalEdge" not in dependency
    assert dependency.count("Canvas {") == 1
