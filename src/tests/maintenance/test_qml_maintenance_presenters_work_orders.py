from pathlib import Path
from types import SimpleNamespace

from src.api.desktop.runtime import build_desktop_api_registry
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


def test_maintenance_workspace_catalog_exposes_typed_work_requests_controller(
    services,
) -> None:
    site = services["site_service"].create_site(
        site_code="MNT-WR",
        name="Maintenance Request Site",
        city="Leipzig",
        currency_code="EUR",
    )
    work_requests_api = build_maintenance_work_requests_desktop_api(
        work_request_service=services["maintenance_work_request_service"],
        site_service=services["site_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
    )
    work_requests_api.create_work_request(
        MaintenanceWorkRequestCreateCommand(
            site_id=site.id,
            work_request_code="WR-QML-001",
            request_type="CORRECTIVE",
            title="Planner intake request",
            description="Requires first triage.",
            priority="HIGH",
            source_type="MANUAL",
        )
    )
    catalog = MaintenanceWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            maintenance_work_requests=work_requests_api,
        )
    )

    controller = catalog.workRequestsWorkspace

    assert controller.workspace["routeId"] == "maintenance_management.work_requests"
    assert controller.workspace["migrationStatus"] == "QML work-request slice active"
    assert controller.overview["title"] == "Work Requests"
    assert controller.siteOptions[1]["label"] == "MNT-WR - Maintenance Request Site"
    assert controller.workRequests["items"][0]["title"] == "WR-QML-001"
    assert controller.selectedWorkRequest["state"]["requestType"] == "CORRECTIVE"

    controller.setSearchText("planner")

    assert controller.searchText == "planner"


def test_maintenance_workspace_catalog_exposes_typed_work_orders_controller(
    services,
) -> None:
    site = services["site_service"].create_site(
        site_code="MNT-WO",
        name="Maintenance Order Site",
        city="Dresden",
        currency_code="EUR",
    )
    work_orders_api = build_maintenance_work_orders_desktop_api(
        work_order_service=services["maintenance_work_order_service"],
        work_request_service=services["maintenance_work_request_service"],
        site_service=services["site_service"],
        employee_service=services["employee_service"],
        party_service=services["party_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
    )
    work_orders_api.create_work_order(
        MaintenanceWorkOrderCreateCommand(
            site_id=site.id,
            work_order_code="WO-QML-001",
            work_order_type="CORRECTIVE",
            source_type="MANUAL",
            title="Execution planning candidate",
            description="Needs planning review.",
            priority="HIGH",
        )
    )
    catalog = MaintenanceWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            maintenance_work_orders=work_orders_api,
        )
    )

    controller = catalog.workOrdersWorkspace

    assert controller.workspace["routeId"] == "maintenance_management.work_orders"
    assert controller.workspace["migrationStatus"] == "QML work-order slice active"
    assert controller.overview["title"] == "Work Orders"
    assert controller.siteOptions[1]["label"] == "MNT-WO - Maintenance Order Site"
    assert controller.workOrders["items"][0]["title"] == "WO-QML-001"
    assert controller.selectedWorkOrder["state"]["workOrderType"] == "CORRECTIVE"

    controller.setSearchText("planning")

    assert controller.searchText == "planning"
