"""R3.4: Portfolio IA tabs (Executive/Heatmap/Intake/Scenarios/Capacity/
Dependencies) replacing the old fixed bottom panel. Driven through real QML
loads of the canonical shell's Portfolio compatibility route, matching the
R2.8 discipline of not relying only on source-contract tests."""

from __future__ import annotations

import os

from PySide6.QtGui import QGuiApplication

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine

_TAB_KEYS = ("executive", "heatmap", "intake", "scenarios", "capacity", "dependencies")


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-r3-4-test"])


def _load_portfolio_route(services):
    _ensure_qgui_application()
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()
    routes = {route.route_id: route for route in build_project_management_routes()}

    engine = create_qml_engine()
    engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
    engine.load(str(routes["project_management.portfolio"].qml_path))
    return engine, pm_catalog


def test_portfolio_route_loads_with_six_tab_ia(services) -> None:
    engine, pm_catalog = _load_portfolio_route(services)

    assert len(engine.rootObjects()) == 1
    controller = pm_catalog.portfolioWorkspace
    assert controller.activeTab == "executive"


def test_switching_every_portfolio_tab_does_not_error(services) -> None:
    """Each of the 6 tabs must be reachable via setActiveTab() and must
    round-trip through a real refresh() without raising -- this is the
    behavior a real StackLayout + DetailTabBar click would trigger."""
    engine, pm_catalog = _load_portfolio_route(services)
    assert len(engine.rootObjects()) == 1
    controller = pm_catalog.portfolioWorkspace

    for tab_key in _TAB_KEYS:
        controller.setActiveTab(tab_key)
        assert controller.activeTab == tab_key
        assert controller.errorMessage == ""


def test_heatmap_tab_pagination_state_is_exposed_after_load(services) -> None:
    engine, pm_catalog = _load_portfolio_route(services)
    assert len(engine.rootObjects()) == 1
    controller = pm_catalog.portfolioWorkspace

    controller.setActiveTab("heatmap")
    assert controller.heatmapPage == 1
    assert controller.heatmapPageSize > 0

    controller.setActiveTab("intake")
    assert controller.intakePage == 1
    assert controller.intakePageSize > 0

    controller.setActiveTab("dependencies")
    assert controller.dependencyPage == 1
    assert controller.dependencyPageSize > 0


