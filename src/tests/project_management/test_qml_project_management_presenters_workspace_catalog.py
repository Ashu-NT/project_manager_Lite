import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QSettings

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.presenters import (
    build_project_management_workspace_presenters,
)
from src.ui_qml.modules.project_management.navigation import PM_CANONICAL_ROUTE_ID
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.modules.project_management.domain.enums import (
    CostType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)


def test_project_management_workspace_presenters_match_qml_routes() -> None:
    routes = build_project_management_routes()
    presenters = build_project_management_workspace_presenters()

    assert list(presenters) == [route.route_id for route in routes]

    for route in routes:
        view_model = presenters[route.route_id].build_view_model()
        assert view_model.route_id == route.route_id
        assert view_model.title == route.title
        # R2.7: the canonical shell route is a pure UI composition, not one
        # of the ten backend-tracked capability workspaces, so it has no
        # ProjectManagementWorkspaceDesktopApi descriptor/summary. That's
        # correct, not a gap -- assert the absence explicitly rather than
        # silently exempt it.
        if route.route_id == PM_CANONICAL_ROUTE_ID:
            assert view_model.summary == ""
        else:
            assert view_model.summary
        assert view_model.migration_status == "QML landing zone ready"
        assert view_model.legacy_runtime_status == "Existing QWidget screen remains active"


def test_project_management_workspace_catalog_exposes_qml_safe_maps() -> None:
    catalog = ProjectManagementWorkspaceCatalog()

    workspace = catalog.workspace("project_management.projects")

    assert workspace == {
        "routeId": "project_management.projects",
        "title": "Projects",
        "summary": "Project lifecycle, ownership, status, and project list workflows.",
        "migrationStatus": "QML landing zone ready",
        "legacyRuntimeStatus": "Existing QWidget screen remains active",
    }


def test_project_management_workspace_catalog_returns_no_capabilities_without_active_organization(
    services,
) -> None:
    services["user_session"].set_active_organization_id(None)
    registry = build_desktop_api_registry(services)
    catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)

    assert catalog.isModuleEnabled("project_management") is False
    assert catalog.hasCapability("inventory.stock.read") is False
    assert (
        catalog.canUseIntegration(
            "project_management",
            "inventory_procurement",
            "material_demand",
        )
        is False
    )


def test_project_management_workspace_catalog_owns_live_project_context_and_navigation(
    services,
) -> None:
    """R2.3: PMProjectContextController and PMWorkspaceNavigationController
    are catalog-owned and wired to the REAL Projects desktop API, not a
    fake/local project list."""
    project = services["project_service"].create_project("Plant Upgrade")
    registry = build_desktop_api_registry(services)
    catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)

    assert catalog.pmProjectContext is not None
    assert catalog.pmNavigation is not None
    assert catalog.pmProjectContext.hasActiveProject is False

    catalog.pmProjectContext.refreshProjects()
    option_ids = {option["id"] for option in catalog.pmProjectContext.projectOptions}
    assert project.id in option_ids

    assert catalog.pmProjectContext.selectProject(project.id) is True
    assert catalog.pmProjectContext.activeProjectId == project.id

    # Planning (scheduling) is REQUIRED; Dashboard (overview) is OPTIONAL.
    catalog.pmNavigation.selectWorkspace("scheduling")
    assert catalog.projectContextRequirementSatisfied is True
    catalog.pmProjectContext.clearProject()
    assert catalog.projectContextRequirementSatisfied is False

    catalog.pmNavigation.selectWorkspace("dashboard")
    assert catalog.projectContextRequirementSatisfied is True


def test_refresh_capabilities_preserves_still_accessible_active_project(services) -> None:
    """R2.4: tenant/organization-change transitions route through
    refreshCapabilities() (see shell/app.py's tenantSwitched/
    organizationsChanged wiring). A still-valid active project must survive
    that refresh, not be silently cleared."""
    project = services["project_service"].create_project("Plant Upgrade")
    registry = build_desktop_api_registry(services)
    catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    catalog.pmProjectContext.refreshProjects()
    catalog.pmProjectContext.selectProject(project.id)

    catalog.refreshCapabilities()

    assert catalog.pmProjectContext.activeProjectId == project.id
    assert catalog.pmProjectContext.hasActiveProject is True


def test_refresh_capabilities_clears_project_that_became_inaccessible(services) -> None:
    project = services["project_service"].create_project("Plant Upgrade")
    registry = build_desktop_api_registry(services)
    catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    catalog.pmProjectContext.refreshProjects()
    catalog.pmProjectContext.selectProject(project.id)

    services["project_service"].delete_project(project.id)
    catalog.refreshCapabilities()

    assert catalog.pmProjectContext.hasActiveProject is False
    assert catalog.pmProjectContext.activeProjectId == ""


def test_refresh_all_workspaces_reauthentication_path_revalidates_project(services) -> None:
    """R2.4: refreshAllWorkspaces() is the reauthentication transition
    (ShellRuntimeSessionController calls it only after a session that had
    expired successfully re-authenticates)."""
    project = services["project_service"].create_project("Plant Upgrade")
    registry = build_desktop_api_registry(services)
    catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    catalog.pmProjectContext.refreshProjects()
    catalog.pmProjectContext.selectProject(project.id)

    catalog.refreshAllWorkspaces()

    assert catalog.pmProjectContext.activeProjectId == project.id


def test_project_context_fails_safe_without_projects_api() -> None:
    """No desktop API registry wired (e.g. QML preview) must not crash a
    refresh and must not fabricate an active project."""
    catalog = ProjectManagementWorkspaceCatalog()

    catalog.refreshCapabilities()
    catalog.refreshAllWorkspaces()

    assert catalog.pmProjectContext.hasActiveProject is False
    assert catalog.pmProjectContext.validationStatus == "unavailable"


def test_project_management_workspace_catalog_returns_empty_unknown_workspace() -> None:
    catalog = ProjectManagementWorkspaceCatalog()

    workspace = catalog.workspace("project_management.unknown")

    assert workspace["routeId"] == "project_management.unknown"
    assert workspace["title"] == ""
    assert workspace["summary"] == ""


def test_project_management_qml_presenters_do_not_import_legacy_widget_or_infra() -> None:
    source_root = Path("src/ui_qml/modules/project_management")
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in source_root.rglob("*.py")
        if "__pycache__" not in path.parts
    )

    assert "src.ui.modules.project_management" not in source_text
    assert "ui.modules.project_management" not in source_text
    assert "infrastructure.persistence" not in source_text
    assert "repositories" not in source_text


def test_project_management_qml_uses_named_modules_and_typed_catalog_properties() -> None:
    qml_root = Path("src/ui_qml/modules/project_management/qml")
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in qml_root.rglob("*.qml")
        if "__pycache__" not in path.parts
    )

    assert "import ProjectManagement.Controllers 1.0" in qml_text
    assert 'import "dialogs" as TaskDialogs' in qml_text
    assert "import ProjectManagement.Widgets 1.0" in qml_text
    assert "property var pmCatalog" not in qml_text
    assert "Risks, issues, and changes — unified project governance register." in qml_text
    assert "Task planning, progress, dependencies, assignments, and execution state." in qml_text
    assert "Enterprise planning and schedule control workspace." in qml_text
    assert 'searchPlaceholder: "Search tasks..."' in qml_text
    assert "showCustomize: true" in qml_text
    assert "showViews: true" in qml_text
    assert "showExport: true" in qml_text
    assert "AppWidgets.BulkActionBar {" in qml_text
    assert "AppWidgets.BulkChangePropertyPopup {" in qml_text
    assert "Project KPIs, health summaries, and executive delivery views." in qml_text
