from pathlib import Path
from types import SimpleNamespace

from src.application.runtime import build_desktop_api_registry
from src.core.modules.maintenance.api.desktop import (
    MaintenanceLocationCreateCommand,
    MaintenancePreventivePlanCreateCommand,
    MaintenancePreventivePlanTaskCreateCommand,
    MaintenanceTaskTemplateCreateCommand,
    MaintenanceWorkRequestCreateCommand,
    MaintenanceWorkOrderCreateCommand,
    build_maintenance_assets_desktop_api,
    build_maintenance_dashboard_desktop_api,
    build_maintenance_planner_desktop_api,
    build_maintenance_preventive_desktop_api,
    build_maintenance_reliability_desktop_api,
    build_maintenance_work_orders_desktop_api,
    build_maintenance_work_requests_desktop_api,
)
from src.ui_qml.modules.maintenance.context import MaintenanceWorkspaceCatalog
from src.ui_qml.modules.maintenance.presenters import (
    MaintenancePreventiveWorkspacePresenter,
    build_maintenance_workspace_presenters,
)
from src.ui_qml.modules.maintenance.routes import build_maintenance_routes
from src.ui_qml.modules.maintenance.view_models import (
    MaintenancePreventiveWorkspaceViewModel,
)


def test_maintenance_workspace_presenters_match_qml_routes() -> None:
    routes = build_maintenance_routes()
    presenters = build_maintenance_workspace_presenters()

    assert list(presenters) == [route.route_id for route in routes]

    for route in routes:
        view_model = presenters[route.route_id].build_view_model()
        assert view_model.route_id == route.route_id
        assert view_model.title == route.title
        assert view_model.summary
        assert view_model.legacy_runtime_status == "Existing QWidget workspace remains active"


def test_maintenance_workspace_catalog_exposes_qml_safe_maps() -> None:
    catalog = MaintenanceWorkspaceCatalog()

    workspace = catalog.workspace("maintenance_management.assets")

    assert workspace == {
        "routeId": "maintenance_management.assets",
        "title": "Assets",
        "summary": "Sites, locations, systems, assets, and component-library structures for maintenance scope.",
        "migrationStatus": "QML asset-library slice active",
        "legacyRuntimeStatus": "Existing QWidget workspace remains active",
    }


def test_maintenance_workspace_catalog_returns_empty_unknown_workspace() -> None:
    catalog = MaintenanceWorkspaceCatalog()

    workspace = catalog.workspace("maintenance_management.unknown")

    assert workspace["routeId"] == "maintenance_management.unknown"
    assert workspace["title"] == ""


def test_maintenance_qml_presenters_do_not_import_legacy_widget_or_infrastructure() -> None:
    source_root = Path("src/ui_qml/modules/maintenance")
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(source_root.rglob("*.py"))
        if "__pycache__" not in path.parts
    )

    assert "src.ui.modules.maintenance" not in source_text
    assert "ui.modules.maintenance_management" not in source_text
    assert ".infrastructure." not in source_text
    assert ".repositories" not in source_text


def test_maintenance_qml_uses_named_modules_and_typed_catalog_properties() -> None:
    qml_root = Path("src/ui_qml/modules/maintenance/qml")
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(qml_root.rglob("*.qml"))
    )

    assert "import Maintenance.Controllers 1.0" in combined
    assert "property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog" in combined
    assert "property var maintenanceCatalog" not in combined


def test_maintenance_routes_are_in_desktop_registry(services) -> None:
    registry = build_desktop_api_registry(services)

    assert registry.maintenance_workspaces.list_workspaces()[0].key == "dashboard"
    assert registry.maintenance_dashboard.build_snapshot().overview.title == "Maintenance Dashboard"
    assert registry.maintenance_planner.build_snapshot().overview.title == "Planner"
    assert registry.maintenance_preventive.list_plan_statuses()[0].value == "DRAFT"
    assert registry.maintenance_reliability.build_snapshot().overview.title == "Reliability"
    assert registry.maintenance_work_requests.list_statuses()[0].value == "NEW"
    assert registry.maintenance_work_orders.list_statuses()[0].value == "DRAFT"
