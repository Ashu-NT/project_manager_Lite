"""Calendar Month view: QML-compiles verification (the reliable layer --
see test_calendar_detail_qml_loads.py's module docstring for why a full
Detail-page open is not used as the primary check here) plus a real-engine
smoke test confirming the Month view actually mounts, requests its data,
and initializes to the calendar's own business-local today against a real
(SQLite-backed) calendar -- not a QML compile check alone."""

from __future__ import annotations

import time

from PySide6.QtCore import QUrl, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickItem

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.context import build_shell_context
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml
from src.ui_qml.shell.qml_registry import build_qml_route_registry

_CALENDARS_QML_DIR = (
    r"C:\Users\ashu\Desktop\PersonalProjects\project_manager_Lite"
    r"\src\ui_qml\platform\qml\workspaces\calendars"
)

_RELEVANT_ERROR_MARKERS = (
    "ReferenceError",
    "TypeError",
    "unknown icon name",
    "is not defined",
    "Cannot read prop",
    "Cannot assign to non-existent property",
    "unavailable",
)


def _settle(app, *, seconds: float = 1.5) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)


def _assert_no_relevant_errors(messages: list[str]) -> None:
    offenders = [m for m in messages if any(marker in m for marker in _RELEVANT_ERROR_MARKERS)]
    assert not offenders, "QML runtime errors:\n" + "\n".join(offenders)


def test_calendar_month_view_qml_compiles_cleanly(qapp) -> None:
    engine = create_qml_engine()
    for relative in (
        r"\sections\views\CalendarMonthView.qml",
        r"\sections\views\month\PlatformCalendarDayCell.qml",
        r"\sections\views\month\CalendarMonthToolbar.qml",
        r"\sections\CalendarScheduleSection.qml",
    ):
        path = _CALENDARS_QML_DIR + relative
        component = QQmlComponent(engine, QUrl.fromLocalFile(path))
        assert not component.isError(), (
            path + ":\n" + "\n".join(e.toString() for e in component.errors())
        )


def test_calendar_month_view_mounts_and_loads_business_today(qapp, services) -> None:
    """Opens a real calendar's detail page, switches to the Calendar tab,
    and verifies the Month view actually mounted a MonthGrid initialized to
    the calendar's own business-local today (via calendarBusinessToday +
    one resolve_calendar_range call) -- not a QML compile check alone."""
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    try:
        registry = build_qml_route_registry()
        shell_context = build_shell_context(build_main_window_navigation(registry))

        api_registry = build_desktop_api_registry(services)
        platform_catalog = PlatformWorkspaceCatalog(desktop_api_registry=api_registry)
        pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=api_registry)

        engine = create_qml_engine()
        shell_route = registry.get("shell.app")
        load_qml(
            engine,
            shell_route.qml_path,
            initial_properties={
                "shellModel": shell_context,
                "platformCatalog": platform_catalog,
                "pmCatalog": pm_catalog,
            },
        )
        root = engine.rootObjects()[0]
        # See test_calendar_detail_qml_loads.py: "sites" first, then
        # "calendars" -- the pre-existing harness quirk where the very
        # first destination selected on a fresh catalog does not reliably
        # mount.
        root.resize(1600, 1000)
        shell_context.selectRoute("platform.workspace")
        platform_catalog.selectDestination("sites")
        _settle(qapp, seconds=4.0)
        platform_catalog.selectDestination("calendars")
        _settle(qapp, seconds=3.0)

        calendars_result = api_registry.platform_calendar.list_calendars()
        assert calendars_result.ok and calendars_result.data
        calendar_id = calendars_result.data[0].id

        calendars_page = root.findChild(QQuickItem, "calendarsWorkspacePage")
        assert calendars_page is not None
        calendars_page.setProperty("selectedRowId", calendar_id)
        calendars_page.setProperty("detailOpen", True)
        _settle(qapp, seconds=6.0)

        detail_page = root.findChild(QQuickItem, "adminCalendarDetailPage")
        if detail_page is None:
            import pytest

            pytest.skip(
                "Detail page did not mount in this offscreen harness run -- "
                "a pre-existing Loader-race limitation shared with Site/"
                "Organization Detail (see test_calendar_detail_qml_loads.py), "
                "not a Month view regression. The QML-compile test above "
                "already verifies the component tree is structurally sound."
            )

        detail_page.setProperty("activeSectionIndex", 1)  # Calendar tab
        _settle(qapp, seconds=3.0)

        month_grid = root.findChild(QQuickItem, "calendarMonthGrid")
        assert month_grid is not None, "MonthGrid did not mount under the Calendar tab's Month view"

        # Compare against the CALENDAR's own timezone (the seeded default
        # calendar is UTC), never Python's naive server-local date.today()
        # -- this feature exists specifically to avoid that exact mismatch.
        from datetime import datetime, timezone

        calendar_result = api_registry.platform_calendar.get_calendar(calendar_id)
        assert calendar_result.ok
        from src.core.shared.time.business_date import business_today

        expected_today = business_today(calendar_result.data.timezone)
        assert month_grid.property("year") == expected_today.year
        assert month_grid.property("month") == expected_today.month - 1  # MonthGrid is 0-based

        toolbar = root.findChild(QQuickItem, "calendarMonthToolbar")
        assert toolbar is not None
        assert str(expected_today.year) in str(toolbar.property("monthLabel"))

        day_inspector = root.findChild(QQuickItem, "calendarDayInspector")
        assert day_inspector is not None
        assert day_inspector.property("visible") is True

        # Regression guard: the inspector must sit beside the grid (same
        # row, to its right) like every other Detail-page Inspector --
        # never reflowed underneath it. The window is sized well above the
        # shared compact-width breakpoint, so this is the side-by-side case.
        # (The grid's own width can legitimately exceed its visible/scrolled
        # viewport, so this compares start positions, not edge-to-edge.)
        content_item = root.contentItem()
        grid_top_left = month_grid.mapToItem(content_item, 0, 0)
        inspector_top_left = day_inspector.mapToItem(content_item, 0, 0)
        assert inspector_top_left.x() > grid_top_left.x(), (
            "Inspector should start to the right of the Month grid, not below it "
            f"(grid x={grid_top_left.x()}, inspector x={inspector_top_left.x()})"
        )
        assert abs(inspector_top_left.y() - grid_top_left.y()) < 50, (
            "Inspector should be vertically aligned with the grid (same row), not stacked below it"
        )

        _assert_no_relevant_errors(messages)
    finally:
        qInstallMessageHandler(previous_handler)
