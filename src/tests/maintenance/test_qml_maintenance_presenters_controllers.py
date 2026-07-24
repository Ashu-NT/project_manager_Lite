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


def test_maintenance_workspace_catalog_exposes_typed_assets_controller(
    services,
) -> None:
    site = services["site_service"].create_site(
        site_code="MNT-AST",
        name="Maintenance Asset Site",
        city="Cologne",
        currency_code="EUR",
    )

    assets_api = build_maintenance_assets_desktop_api(
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
        site_service=services["site_service"],
        party_service=services["party_service"],
    )

    assets_api.create_location(
        MaintenanceLocationCreateCommand(
            site_id=site.id,
            location_code="LOC-QML-001",
            name="Asset Library Area",
            location_type="PRODUCTION",
        )
    )

    catalog = MaintenanceWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            maintenance_assets=assets_api,
        )
    )

    controller = catalog.assetsWorkspace

    assert controller.workspace["routeId"] == "maintenance_management.assets"
    assert controller.workspace["migrationStatus"] == "QML asset-library slice active"
    assert controller.overview["title"] == "Assets"
    assert controller.siteOptions[1]["label"] == "MNT-AST - Maintenance Asset Site"
    assert controller.locations["items"][0]["title"] == "LOC-QML-001 - Asset Library Area"

    controller.setActiveFilter("active")

    assert controller.selectedActiveFilter == "active"


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