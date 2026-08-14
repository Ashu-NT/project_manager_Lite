"""Regression test for a real production bug: Overview/Dashboard is the
default landing capability inside the PM canonical shell
(ProjectManagementWorkspacePage.qml), so its Loader activates earlier than
any other capability -- often before the shell has finished assigning
pmCatalog onto the outer shell page. The shell's Loader.onLoaded handler
used to do a plain "=" snapshot assignment (`item.pmCatalog =
root.pmCatalog`), which captures whatever root.pmCatalog happened to be at
that instant and then never updates -- if that instant was before pmCatalog
landed, the Dashboard page's pmCatalog stayed null forever, its
ensureLoaded() never found a non-null workspaceController, and
_refresh_dashboard() never ran (confirmed live via the app's own log file:
zero "PM dashboard refresh complete" entries across repeated real launches).
The fix replaced the snapshot with a live Qt.binding() so a late
pmCatalog assignment still reaches the loaded capability page."""

from __future__ import annotations

import os

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-workspace-late-catalog-binding-test"])


def test_dashboard_loads_even_when_pmcatalog_is_assigned_after_shell_page_completes(
    services,
) -> None:
    qapp = _ensure_qgui_application()
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()
    routes = {route.route_id: route for route in build_project_management_routes()}

    engine = create_qml_engine()
    # Deliberately do NOT set pmCatalog via setInitialProperties -- this
    # reproduces the real shell's timing, where the canonical workspace
    # page's own Component.onCompleted (and its Dashboard Loader's
    # activation) can run before pmCatalog is assigned.
    engine.setInitialProperties({"platformCatalog": platform_catalog})
    engine.load(str(routes["project_management.workspace"].qml_path))
    assert len(engine.rootObjects()) == 1
    root_object = engine.rootObjects()[0]

    QCoreApplication.processEvents()
    assert pm_catalog.dashboardWorkspace.hasLoaded is False

    # The shell assigns pmCatalog only now -- after the page (and its
    # already-activated Dashboard Loader) already completed construction.
    root_object.setProperty("pmCatalog", pm_catalog)
    QCoreApplication.processEvents()
    QCoreApplication.processEvents()

    controller = pm_catalog.dashboardWorkspace
    assert controller.hasLoaded is True
    assert controller.errorMessage == ""
