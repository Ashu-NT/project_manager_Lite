from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication

from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml
from src.ui_qml.shell.qml_registry import build_qml_route_registry


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


def _read(relative_path: str) -> str:
    return (SCHEDULING_ROOT / relative_path).read_text(encoding="utf-8")


def _without_line_comments(text: str) -> str:
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["qml-scheduling-responsive-test"])


def test_planning_navigation_and_header_match_the_approved_information_architecture() -> None:
    state = _read("SchedulingWorkspaceState.qml")
    page = _read("SchedulingWorkspacePage.qml")
    header = _read("components/SchedulingPlanningContextHeader.qml")

    primary = state.split("readonly property var primaryPanelTabs:", 1)[1].split("]", 1)[0]
    secondary = state.split("readonly property var secondaryPanelTabs:", 1)[1].split("]", 1)[0]

    assert [primary.index(label) for label in ('"Overview"', '"Gantt"', '"Resource Leveling"', '"Diagnostics"')] == sorted(
        primary.index(label)
        for label in ('"Overview"', '"Gantt"', '"Resource Leveling"', '"Diagnostics"')
    )
    assert [secondary.index(label) for label in ('"Baselines"', '"Calendars"', '"Activity Feed"')] == sorted(
        secondary.index(label)
        for label in ('"Baselines"', '"Calendars"', '"Activity Feed"')
    )
    assert '"id": "delays"' not in state.lower()
    assert '"id": "resources"' not in state.lower()
    assert "AppWidgets.NavOverflowMenu" in page
    assert "activeId:     state.activePanelId" in page
    assert page.count("Components.SchedulingPlanningContextHeader") == 1

    assert header.count('"id": "refresh"') == 1
    assert header.count('"id": "run_cpm"') == 1
    assert "workspaceController.refresh()" in header
    assert "workspaceController.recalculateSchedule()" in header
    assert "workspaceController.selectProject" in header
    assert "selectCalendar" not in header
    assert "selectBaseline" not in header


def test_gantt_has_truthful_controls_lazy_impact_and_no_fake_baseline_rendering() -> None:
    gantt = _read("panels/SchedulingGanttPanel.qml")
    surface = _read("components/gantt/SchedulingGanttSurface.qml")
    row = _read("components/gantt/SchedulingGanttRow.qml")
    gantt_code = _without_line_comments(gantt)
    surface_code = _without_line_comments(surface)
    row_code = _without_line_comments(row)

    assert 'text: "Delayed only"' in gantt
    assert 'text: "Critical only"' in gantt
    assert 'text: "Analyze Impact"' in gantt
    assert "workspaceController.computeScheduleImpact" in gantt
    assert "root.scheduleImpact.taskId" in gantt

    assert "workspaceController.ganttRowsModel" in surface
    assert "root.workspaceController.selectActivity(taskId)" in gantt
    assert "TablePaginationBar" not in gantt
    assert "AppWidgets.DataTable" not in gantt

    for fake_control in ("Baseline overlay", "Highlight Critical Path"):
        assert fake_control not in gantt_code
        assert fake_control not in surface_code
    assert 'text: "Dependency Lines"' in gantt_code
    assert "SchedulingGanttDependencyLayer" in surface_code
    assert 'text: "Scale"' in gantt_code
    assert 'text: "Today"' in gantt_code
    assert "ganttSurface.zoomIn()" in gantt_code
    assert "ganttSurface.zoomOut()" in gantt_code
    assert "ganttSurface.setTimescale" in gantt_code
    assert "baselinePlaceholder" not in row_code
    assert "baseline_placeholder" not in row_code
    assert "isMilestone: root.isMilestone" in row
    assert "startDayOrdinal === finishDayOrdinal" not in row


def test_planning_responsive_contract_and_retired_panels_remain_enforced() -> None:
    gantt = _read("panels/SchedulingGanttPanel.qml")
    surface = _read("components/gantt/SchedulingGanttSurface.qml")

    assert "compactContentBreakpoint" in gantt
    assert 'root.requestedViewMode === "split"' in surface
    assert "root.splitAvailable" in surface
    assert "AppWidgets.SlideOverPanel" in gantt
    assert "root.hasSelection && !root.inspectorInline" in gantt
    assert "root.hasSelection\n        && root.width >= Theme.AppTheme.inspectorWidth" in gantt
    assert "Theme.AppTheme.inspectorWidth + Theme.AppTheme.spacingSm + 1024" in gantt

    for retired_panel in (
        "SchedulingActivityTimelinePanel.qml",
        "SchedulingDelaysPanel.qml",
        "SchedulingDetailPanel.qml",
        "SchedulingResourcesPanel.qml",
        "SchedulingTimelinePanel.qml",
    ):
        assert not (SCHEDULING_ROOT / "panels" / retired_panel).exists()


@pytest.mark.parametrize(
    ("width", "height"),
    ((1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)),
)
def test_registered_planning_route_loads_at_supported_viewport(width: int, height: int) -> None:
    application = _ensure_qgui_application()
    route = build_qml_route_registry().get("project_management.scheduling")
    engine = create_qml_engine()

    load_qml(engine, route.qml_path)
    root = engine.rootObjects()[0]
    assert root.setProperty("width", width)
    assert root.setProperty("height", height)
    application.processEvents()

    assert int(root.property("width")) == width
    assert int(root.property("height")) == height
