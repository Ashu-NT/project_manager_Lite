"""R2.6-R2.10/R2.12 acceptance tests for the canonical PM shell, driven
through actual QML loads (not just Python/source-contract checks) -- per
the explicit R2.8 instruction not to rely only on source-contract tests."""

from __future__ import annotations

import os

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_workspace_controller import (
    ProjectManagementDashboardWorkspaceController,
)
from src.ui_qml.modules.project_management.controllers.projects.projects_workspace_controller import (
    ProjectManagementProjectsWorkspaceController,
)
from src.ui_qml.modules.project_management.controllers.scheduling.scheduling_workspace_controller import (
    ProjectManagementSchedulingWorkspaceController,
)
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine


EXPECTED_DESTINATION_BY_ROUTE = {
    "project_management.dashboard": ("dashboard", "overview", ""),
    "project_management.portfolio": ("portfolio", "portfolio", ""),
    "project_management.projects": ("projects", "work", "projects"),
    "project_management.tasks": ("tasks", "work", "tasks"),
    "project_management.scheduling": ("scheduling", "work", "planning"),
    "project_management.resources": ("resources", "workload", "resources"),
    "project_management.timesheets": ("timesheets", "workload", "review_queue"),
    "project_management.financials": ("financials", "finance", ""),
    "project_management.register": ("register", "governance", "register"),
    "project_management.collaboration": ("collaboration", "governance", "collaboration"),
}


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-r2-test"])


def _instrument_construction(cls):
    counts = {"n": 0}
    real_init = cls.__init__

    def counting_init(self, *args, **kwargs):
        counts["n"] += 1
        real_init(self, *args, **kwargs)

    cls.__init__ = counting_init

    def restore():
        cls.__init__ = real_init

    return counts, restore


def test_canonical_route_loads_and_defaults_to_dashboard_overview(services) -> None:
    _ensure_qgui_application()
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()

    routes = {route.route_id: route for route in build_project_management_routes()}
    canonical = routes["project_management.workspace"]

    engine = create_qml_engine()
    engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
    engine.load(str(canonical.qml_path))

    assert len(engine.rootObjects()) == 1
    assert pm_catalog.pmNavigation.workspaceKey == "dashboard"
    assert pm_catalog.pmNavigation.destinationId == "overview"


def test_all_ten_compatibility_routes_load_canonical_shell_with_correct_destination(services) -> None:
    """R2.8: every compatibility route id resolves into the SAME canonical shell
    (not the bare capability page) with the correct PM-local destination
    selected -- proven by actually loading each route's real qml_path."""
    _ensure_qgui_application()
    routes = {route.route_id: route for route in build_project_management_routes()}

    for route_id, (workspace_key, destination_id, secondary_id) in EXPECTED_DESTINATION_BY_ROUTE.items():
        registry = build_desktop_api_registry(services)
        pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
        platform_catalog = PlatformWorkspaceCatalog()

        engine = create_qml_engine()
        engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
        engine.load(str(routes[route_id].qml_path))

        assert len(engine.rootObjects()) == 1, route_id
        assert pm_catalog.pmNavigation.workspaceKey == workspace_key, route_id
        assert pm_catalog.pmNavigation.destinationId == destination_id, route_id
        assert pm_catalog.pmNavigation.secondaryId == secondary_id, route_id


def test_compatibility_route_does_not_pin_active_project(services) -> None:
    """A compatibility-route deep link selecting a destination must not, by itself,
    change the shared PM active-project context (R2.10)."""
    _ensure_qgui_application()
    routes = {route.route_id: route for route in build_project_management_routes()}
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()

    engine = create_qml_engine()
    engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
    engine.load(str(routes["project_management.tasks"].qml_path))

    assert len(engine.rootObjects()) == 1
    assert pm_catalog.pmProjectContext.hasActiveProject is False


def test_required_destination_without_project_shows_dedicated_state(services) -> None:
    """R2.9: Planning (scheduling) is REQUIRED. With no active project the
    dedicated ProjectContextRequiredState must be visible; selecting a
    project must hide it -- proven at the QML object level, not just the
    controller's boolean property."""
    _ensure_qgui_application()
    project = services["project_service"].create_project("Plant Upgrade")
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()

    engine = create_qml_engine()
    engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
    engine.load(
        "src/ui_qml/modules/project_management/qml/workspace/ProjectManagementWorkspace.qml"
    )
    root = engine.rootObjects()[0]
    required_state = root.findChild(QObject, "pmProjectContextRequiredState")
    assert required_state is not None

    pm_catalog.pmNavigation.selectWorkspace("scheduling")
    assert required_state.property("visible") is True
    assert pm_catalog.projectContextRequirementSatisfied is False

    pm_catalog.pmProjectContext.refreshProjects()
    pm_catalog.pmProjectContext.selectProject(project.id)
    assert required_state.property("visible") is False
    assert pm_catalog.projectContextRequirementSatisfied is True

    pm_catalog.pmProjectContext.clearProject()
    assert required_state.property("visible") is True


def test_optional_destination_never_shows_required_state(services) -> None:
    _ensure_qgui_application()
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()

    engine = create_qml_engine()
    engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
    engine.load(
        "src/ui_qml/modules/project_management/qml/workspace/ProjectManagementWorkspace.qml"
    )
    root = engine.rootObjects()[0]
    required_state = root.findChild(QObject, "pmProjectContextRequiredState")

    pm_catalog.pmNavigation.selectWorkspace("tasks")
    assert required_state.property("visible") is False


def test_entering_canonical_shell_only_constructs_the_default_destination(services) -> None:
    """R2.12: constructing/loading the canonical shell must not construct
    (and therefore not refresh/query) any of the nine non-default
    workspace controllers."""
    _ensure_qgui_application()
    counts = {}
    restores = []
    for cls in (
        ProjectManagementProjectsWorkspaceController,
        ProjectManagementSchedulingWorkspaceController,
    ):
        c, r = _instrument_construction(cls)
        counts[cls] = c
        restores.append(r)
    try:
        registry = build_desktop_api_registry(services)
        pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
        platform_catalog = PlatformWorkspaceCatalog()

        engine = create_qml_engine()
        engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
        engine.load(
            "src/ui_qml/modules/project_management/qml/workspace/ProjectManagementWorkspace.qml"
        )
        assert len(engine.rootObjects()) == 1

        assert counts[ProjectManagementProjectsWorkspaceController]["n"] == 0
        assert counts[ProjectManagementSchedulingWorkspaceController]["n"] == 0

        pm_catalog.pmNavigation.selectWorkspace("projects")
        assert counts[ProjectManagementProjectsWorkspaceController]["n"] == 1
        assert counts[ProjectManagementSchedulingWorkspaceController]["n"] == 0
    finally:
        for restore in restores:
            restore()


def test_project_context_bar_search_does_not_pin_only_explicit_pick_does(services) -> None:
    """R2.10/R2.11: typing in the project search box must only call
    searchProjects() (browsing), never selectProject(). Only picking a
    result from the combo (an explicit user action) pins the context."""
    _ensure_qgui_application()
    project = services["project_service"].create_project("Plant Upgrade")
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()

    engine = create_qml_engine()
    engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
    engine.load(
        "src/ui_qml/modules/project_management/qml/workspace/ProjectManagementWorkspace.qml"
    )
    root = engine.rootObjects()[0]
    context_bar = root.findChild(QObject, "pmProjectContextBar")
    assert context_bar is not None

    project_context = context_bar.property("projectContext")
    assert project_context is not None
    project_context.searchProjects("Plant")
    assert pm_catalog.pmProjectContext.hasActiveProject is False

    assert project_context.selectProject(project.id) is True
    assert pm_catalog.pmProjectContext.activeProjectId == project.id


def test_nav_rail_is_manually_collapsible_like_platform(services) -> None:
    """PM's secondary nav reuses App.Widgets.GroupedNavigationRail with
    showRailToggle: true, matching PlatformNavigation.qml's own setup, so
    the user can manually collapse/expand it (in addition to it already
    auto-collapsing at narrow width)."""
    _ensure_qgui_application()
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()

    engine = create_qml_engine()
    engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
    engine.load(
        "src/ui_qml/modules/project_management/qml/workspace/ProjectManagementWorkspace.qml"
    )
    root = engine.rootObjects()[0]
    nav = root.findChild(QObject, "pmWorkspaceNavigation")
    assert nav is not None
    assert nav.property("showRailToggle") is True
    assert nav.property("collapsed") is False

    nav.setProperty("collapsed", True)
    assert nav.property("collapsed") is True


def test_revisiting_a_destination_does_not_reconstruct_its_controller(services) -> None:
    _ensure_qgui_application()
    counts, restore = _instrument_construction(ProjectManagementDashboardWorkspaceController)
    try:
        registry = build_desktop_api_registry(services)
        pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
        platform_catalog = PlatformWorkspaceCatalog()

        engine = create_qml_engine()
        engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
        engine.load(
            "src/ui_qml/modules/project_management/qml/workspace/ProjectManagementWorkspace.qml"
        )
        assert len(engine.rootObjects()) == 1
        assert counts["n"] == 1

        pm_catalog.pmNavigation.selectWorkspace("projects")
        pm_catalog.pmNavigation.selectWorkspace("dashboard")
        assert counts["n"] == 1
    finally:
        restore()
