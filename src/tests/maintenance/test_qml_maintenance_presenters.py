from pathlib import Path
from types import SimpleNamespace

from src.api.desktop.runtime import build_desktop_api_registry
from src.core.modules.maintenance.api.desktop import (
    build_maintenance_dashboard_desktop_api,
    build_maintenance_planner_desktop_api,
    build_maintenance_reliability_desktop_api,
)
from src.ui_qml.modules.maintenance.context import MaintenanceWorkspaceCatalog
from src.ui_qml.modules.maintenance.presenters import (
    build_maintenance_workspace_presenters,
)
from src.ui_qml.modules.maintenance.routes import build_maintenance_routes


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
        "migrationStatus": "QML landing zone ready",
        "legacyRuntimeStatus": "Existing QWidget workspace remains active",
    }


def test_maintenance_workspace_catalog_exposes_typed_dashboard_controller(
    services,
) -> None:
    services["site_service"].create_site(
        site_code="MNT-QML",
        name="Maintenance QML Site",
        city="Berlin",
        currency_code="EUR",
    )
    dashboard_api = build_maintenance_dashboard_desktop_api(
        reliability_service=services["maintenance_reliability_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
    )
    catalog = MaintenanceWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            maintenance_dashboard=dashboard_api,
        )
    )

    controller = catalog.dashboardWorkspace

    assert controller.workspace["routeId"] == "maintenance_management.dashboard"
    assert controller.workspace["migrationStatus"] == "QML analytics dashboard slice active"
    assert controller.overview["title"] == "Maintenance Dashboard"
    assert controller.windowOptions[0]["value"] == "30"
    assert controller.siteOptions[1]["label"] == "MNT-QML - Maintenance QML Site"

    controller.setDaysFilter(180)

    assert controller.selectedDaysFilter == "180"


def test_maintenance_workspace_catalog_exposes_typed_reliability_controller(
    services,
) -> None:
    services["site_service"].create_site(
        site_code="MNT-REL",
        name="Maintenance Reliability Site",
        city="Hamburg",
        currency_code="EUR",
    )
    services["maintenance_failure_code_service"].create_failure_code(
        failure_code="SYM-001",
        name="Seal Leak",
        code_type="symptom",
    )
    reliability_api = build_maintenance_reliability_desktop_api(
        reliability_service=services["maintenance_reliability_service"],
        failure_code_service=services["maintenance_failure_code_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
    )
    catalog = MaintenanceWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            maintenance_reliability=reliability_api,
        )
    )

    controller = catalog.reliabilityWorkspace

    assert controller.workspace["routeId"] == "maintenance_management.reliability"
    assert controller.workspace["migrationStatus"] == "QML reliability analytics slice active"
    assert controller.overview["title"] == "Reliability"
    assert controller.daysOptions[0]["value"] == "30"
    assert controller.failureSymptomOptions[1]["value"] == "SYM-001"

    controller.setFailureCodeFilter("SYM-001")
    controller.setLimitFilter(50)

    assert controller.selectedFailureCodeFilter == "SYM-001"
    assert controller.selectedLimitFilter == "50"


def test_maintenance_workspace_catalog_exposes_typed_planner_controller(
    services,
) -> None:
    services["site_service"].create_site(
        site_code="MNT-PLN",
        name="Maintenance Planner Site",
        city="Bremen",
        currency_code="EUR",
    )
    planner_api = build_maintenance_planner_desktop_api(
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        system_service=services["maintenance_system_service"],
        work_request_service=services["maintenance_work_request_service"],
        work_order_service=services["maintenance_work_order_service"],
        material_requirement_service=services[
            "maintenance_work_order_material_requirement_service"
        ],
        preventive_plan_service=services["maintenance_preventive_plan_service"],
        preventive_generation_service=services[
            "maintenance_preventive_generation_service"
        ],
        reliability_service=services["maintenance_reliability_service"],
        sensor_exception_service=services["maintenance_sensor_exception_service"],
    )
    catalog = MaintenanceWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            maintenance_planner=planner_api,
        )
    )

    controller = catalog.plannerWorkspace

    assert controller.workspace["routeId"] == "maintenance_management.planner"
    assert controller.workspace["migrationStatus"] == "QML planner review slice active"
    assert controller.overview["title"] == "Planner"
    assert controller.requestQueueOptions[0]["value"] == "OPEN_REQUESTS"
    assert controller.workOrderQueueOptions[0]["value"] == "BACKLOG_WORK_ORDERS"
    assert controller.siteOptions[1]["label"] == "MNT-PLN - Maintenance Planner Site"

    controller.setSearchText("seal leak")
    controller.setRequestQueue("ALL_REQUESTS")

    assert controller.searchText == "seal leak"
    assert controller.selectedRequestQueue == "ALL_REQUESTS"


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
    assert registry.maintenance_reliability.build_snapshot().overview.title == "Reliability"
