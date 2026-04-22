from pathlib import Path

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.presenters import (
    ProjectDashboardPresenter,
    build_project_management_workspace_presenters,
)
from src.ui_qml.modules.project_management.routes import build_project_management_routes


def test_project_management_workspace_presenters_match_qml_routes() -> None:
    routes = build_project_management_routes()
    presenters = build_project_management_workspace_presenters()

    assert list(presenters) == [route.route_id for route in routes]

    for route in routes:
        view_model = presenters[route.route_id].build_view_model()
        assert view_model.route_id == route.route_id
        assert view_model.title == route.title
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


def test_project_management_workspace_catalog_returns_empty_unknown_workspace() -> None:
    catalog = ProjectManagementWorkspaceCatalog()

    workspace = catalog.workspace("project_management.unknown")

    assert workspace["routeId"] == "project_management.unknown"
    assert workspace["title"] == ""
    assert workspace["summary"] == ""


def test_project_dashboard_presenter_exposes_empty_overview_view_model() -> None:
    presenter = ProjectDashboardPresenter()

    overview = presenter.build_empty_overview()

    assert overview.title == "Dashboard"
    assert overview.metrics[0].label == "Tasks"
    assert overview.metrics[0].value == "0 / 0"
    assert len(overview.metrics) == 8


def test_project_management_workspace_catalog_exposes_dashboard_overview() -> None:
    catalog = ProjectManagementWorkspaceCatalog()

    overview = catalog.dashboardOverview()

    assert overview["title"] == "Dashboard"
    assert len(overview["metrics"]) == 8
    assert overview["metrics"][0] == {
        "label": "Tasks",
        "value": "0 / 0",
        "supportingText": "Done / Total",
    }


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
