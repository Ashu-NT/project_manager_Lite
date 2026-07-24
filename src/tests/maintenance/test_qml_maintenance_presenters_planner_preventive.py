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