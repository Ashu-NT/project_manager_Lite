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


def test_maintenance_workspace_catalog_exposes_typed_preventive_controller(
    services,
) -> None:
    site = services["site_service"].create_site(
        site_code="MNT-PREV",
        name="Maintenance Preventive Site",
        city="Bonn",
        currency_code="EUR",
    )
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="LOC-PREV-QML",
        name="Preventive Area",
    )
    system = services["maintenance_system_service"].create_system(
        site_id=site.id,
        location_id=location.id,
        system_code="SYS-PREV-QML",
        name="Preventive Line",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        system_id=system.id,
        asset_code="AST-PREV-QML",
        name="Preventive Pump",
    )
    sensor = services["maintenance_sensor_service"].create_sensor(
        site_id=site.id,
        asset_id=asset.id,
        system_id=system.id,
        sensor_code="RUN-HRS-QML",
        sensor_name="Run Hours",
        sensor_type="running_hours",
        source_type="manual",
        unit="H",
    )
    preventive_api = build_maintenance_preventive_desktop_api(
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
        system_service=services["maintenance_system_service"],
        sensor_service=services["maintenance_sensor_service"],
        task_template_service=services["maintenance_task_template_service"],
        task_step_template_service=services["maintenance_task_step_template_service"],
        preventive_plan_service=services["maintenance_preventive_plan_service"],
        preventive_plan_task_service=services["maintenance_preventive_plan_task_service"],
        preventive_generation_service=services["maintenance_preventive_generation_service"],
    )
    task_template = preventive_api.create_task_template(
        MaintenanceTaskTemplateCreateCommand(
            task_template_code="PM-QML-TPL",
            name="Monthly inspection",
            maintenance_type="PREVENTIVE",
            template_status="ACTIVE",
            estimated_minutes=30,
        )
    )
    plan = preventive_api.create_preventive_plan(
        MaintenancePreventivePlanCreateCommand(
            site_id=site.id,
            plan_code="PM-QML-PLAN",
            name="Monthly route",
            asset_id=asset.id,
            system_id=system.id,
            trigger_mode="SENSOR",
            sensor_id=sensor.id,
            sensor_threshold="1000",
            sensor_direction="GREATER_OR_EQUAL",
            generation_horizon_count=3,
            generation_lead_value=1,
            generation_lead_unit="DAYS",
            status="ACTIVE",
        )
    )
    preventive_api.create_plan_task(
        MaintenancePreventivePlanTaskCreateCommand(
            plan_id=plan.id,
            task_template_id=task_template.id,
            sequence_no=1,
            trigger_scope="INHERIT_PLAN",
        )
    )
    catalog = MaintenanceWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            maintenance_preventive=preventive_api,
        )
    )

    controller = catalog.preventiveWorkspace

    assert controller.workspace["routeId"] == "maintenance_management.preventive"
    assert controller.workspace["migrationStatus"] == "QML preventive slice active"
    assert controller.overview["title"] == "Preventive"
    assert controller.queueState["plans"]["items"][0]["title"] == "PM-QML-PLAN - Monthly route"
    assert controller.planLibraryState["plans"]["items"][0]["title"] == "PM-QML-PLAN - Monthly route"
    assert controller.templateLibraryState["templates"]["items"][0]["title"] == "PM-QML-TPL - Monthly inspection"

    controller.setQueueDueStateFilter("DUE")
    controller.selectPlan(plan.id)

    assert controller.queueState["selectedDueStateFilter"] == "DUE"
    assert controller.planLibraryState["selectedPlanId"] == plan.id


def test_maintenance_preventive_presenter_returns_typed_workspace_view_model(
    services,
) -> None:
    preventive_api = build_maintenance_preventive_desktop_api(
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
        system_service=services["maintenance_system_service"],
        sensor_service=services["maintenance_sensor_service"],
        task_template_service=services["maintenance_task_template_service"],
        task_step_template_service=services["maintenance_task_step_template_service"],
        preventive_plan_service=services["maintenance_preventive_plan_service"],
        preventive_plan_task_service=services["maintenance_preventive_plan_task_service"],
        preventive_generation_service=services["maintenance_preventive_generation_service"],
    )
    presenter = MaintenancePreventiveWorkspacePresenter(desktop_api=preventive_api)

    view_model = presenter.build_workspace_state()

    assert isinstance(view_model, MaintenancePreventiveWorkspaceViewModel)
    assert view_model.overview.title == "Preventive"
