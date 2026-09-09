"""Overview/Dashboard is the PM canonical shell's default landing capability
(ProjectManagementWorkspacePage.qml), so its Loader can activate before the shell finishes
assigning `pmCatalog` onto the outer shell page. The Loader must bind `item.pmCatalog` live
via `Qt.binding()`, not a one-time `=` snapshot -- a snapshot captures whatever
`root.pmCatalog` was at that instant and never updates, so a late `pmCatalog` assignment
would leave the Dashboard page's `ensureLoaded()` stuck on a null `workspaceController`."""

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
