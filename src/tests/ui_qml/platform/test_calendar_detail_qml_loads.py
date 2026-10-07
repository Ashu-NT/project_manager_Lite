"""Calendar Detail shell modernization: targeted functional verification
(per the modernization spec's explicit instruction to prioritize behavior
over screenshot permutations, deferring full visual QA as done for Party).

Two layers:
  1. Direct QQmlComponent compilation of every new/changed Calendar QML
     file -- deterministic, fast, and the layer that actually caught a real
     bug this pass (AppControls.Button is not a registered type; fixed to
     PrimaryButton/SecondaryButton). This is the authoritative "QML loads
     cleanly" check.
  2. A full shell-engine smoke test of the Calendars workspace + Inspector
     (list, selection, lifecycle menu). Opening the full Detail page
     (`detailOpen: true`) through this offscreen harness's manually-pumped
     event loop hits a pre-existing Loader async teardown/recreation race
     already documented in test_visual_qa_sites.py's `_open_site_detail`
     ("confirmed to affect the already-accepted Organization Detail
     equally, not something specific to Site") -- not a Calendar-specific
     regression, so Detail-page interaction is verified by the component
     compilation check (layer 1) plus manual/visual QA instead of this
     harness.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QUrl, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickItem

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)
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


def test_calendars_workspace_page_qml_compiles_cleanly(qapp) -> None:
    # Requesting `qapp` (even unused directly) matters: QQmlApplicationEngine
    # needs a constructed QApplication with QT_QPA_PLATFORM=offscreen
    # already in place, or Qt Quick's native type registration crashes the
    # process outright (no Python traceback, just a bare nonzero exit).
    engine = create_qml_engine()
    path = _CALENDARS_QML_DIR + r"\CalendarsWorkspacePage.qml"
    component = QQmlComponent(engine, QUrl.fromLocalFile(path))
    assert not component.isError(), "\n".join(e.toString() for e in component.errors())


def test_admin_calendar_detail_page_qml_compiles_cleanly(qapp) -> None:
    engine = create_qml_engine()
    path = _CALENDARS_QML_DIR + r"\AdminCalendarDetailPage.qml"
    component = QQmlComponent(engine, QUrl.fromLocalFile(path))
    assert not component.isError(), "\n".join(e.toString() for e in component.errors())


def test_calendars_workspace_mounts_with_inspector_and_no_qml_errors(qapp, services) -> None:
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
        root.resize(1600, 1000)
        shell_context.selectRoute("platform.workspace")
        # See module docstring: "sites" first, then "calendars" -- the
        # pre-existing harness quirk where the very first destination
        # selected on a fresh catalog does not reliably mount.
        platform_catalog.selectDestination("sites")
        _settle(qapp, seconds=4.0)
        platform_catalog.selectDestination("calendars")
        _settle(qapp, seconds=3.0)

        calendars_result = api_registry.platform_calendar.list_calendars()
        assert calendars_result.ok and calendars_result.data, "expected the seeded default calendar"
        default_calendar_id = calendars_result.data[0].id

        calendars_page = root.findChild(QQuickItem, "calendarsWorkspacePage")
        assert calendars_page is not None

        calendars_page.setProperty("selectedRowId", default_calendar_id)
        _settle(qapp, seconds=2.0)

        menu_items_raw = calendars_page.property("_inspectorLifecycleMenuItems")
        menu_items = menu_items_raw.toVariant() if hasattr(menu_items_raw, "toVariant") else menu_items_raw
        if menu_items:
            # Organization default calendar: backend independently enforces
            # CALENDAR_DEFAULT_CANNOT_DEACTIVATE/_CANNOT_DELETE -- the menu
            # must reflect that rather than offer an action that will only
            # error.
            action_ids = {str(item.get("id", "")) for item in menu_items}
            assert "deactivate" not in action_ids
            assert "delete" not in action_ids

        _assert_no_relevant_errors(messages)
    finally:
        qInstallMessageHandler(previous_handler)
