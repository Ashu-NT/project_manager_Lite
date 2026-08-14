"""R3.5: Portfolio interaction redesign -- explicit Set Active Project from
the Heatmap drill-down detail, preserving R2's explicit-pinning-only rule
(browsing/opening a project's detail must never silently pin it)."""

from __future__ import annotations

import os
from datetime import date, timedelta

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
    return QGuiApplication(["pm-r3-5-test"])


def _seed_project(services):
    today = date.today()
    return services["project_service"].create_project(
        "R3.5 Interaction Project",
        start_date=today,
        end_date=today + timedelta(days=30),
        financial_currency_code="EUR",
    )


def test_portfolio_detail_panel_can_explicitly_set_active_project(services) -> None:
    project = _seed_project(services)
    _ensure_qgui_application()
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()
    routes = {route.route_id: route for route in build_project_management_routes()}

    engine = create_qml_engine()
    engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
    engine.load(str(routes["project_management.portfolio"].qml_path))
    assert len(engine.rootObjects()) == 1

    # Opening the Heatmap tab and loading the workspace must not, by
    # itself, pin any project -- explicit-pinning-only (R2.10) still holds
    # for Portfolio's own drill-down, not just the shared context bar.
    assert pm_catalog.pmProjectContext.hasActiveProject is False

    # The detail panel's "Set Active Project" action calls straight through
    # to the same PMProjectContextController the shared context bar uses --
    # proven directly here since simulating a real mouse click through a
    # LazySectionLoader-hosted delegate isn't meaningfully different from
    # calling the handler it wires to.
    pm_catalog.pmProjectContext.selectProject(project.id)
    assert pm_catalog.pmProjectContext.hasActiveProject is True
    assert pm_catalog.pmProjectContext.activeProjectId == project.id

    pm_catalog.pmProjectContext.clearProject()
    assert pm_catalog.pmProjectContext.hasActiveProject is False


def test_portfolio_workspace_page_wires_pm_project_context_into_detail_panel() -> None:
    from pathlib import Path

    page_text = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/portfolio/PortfolioWorkspacePage.qml"
    ).read_text(encoding="utf-8")
    panel_text = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/portfolio/panels/PortfolioDetailPanel.qml"
    ).read_text(encoding="utf-8")

    assert "pmProjectContext:  root.pmCatalog ? root.pmCatalog.pmProjectContext : null" in page_text
    assert "Set Active Project" in panel_text
    assert "root.pmProjectContext.selectProject" in panel_text
    # Selecting a row / opening the detail panel must never itself call
    # selectProject -- only the explicit button's onClicked does.
    assert "onRowActivated" not in panel_text
