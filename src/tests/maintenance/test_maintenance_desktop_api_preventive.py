from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetCreateCommand,
    MaintenanceComponentCreateCommand,
    MaintenanceLocationCreateCommand,
    MaintenancePreventiveDesktopApi,
    MaintenancePreventivePlanCreateCommand,
    MaintenancePreventivePlanTaskCreateCommand,
    MaintenanceSystemCreateCommand,
    MaintenanceTaskTemplateCreateCommand,
    build_maintenance_assets_desktop_api,
    build_maintenance_preventive_desktop_api,
)
from src.core.platform.domain.master_data.party import PartyType


def _create_shared_maintenance_references(services):
    site = services["site_service"].create_site(
        site_code="MNT-HQ",
        name="Maintenance HQ",
        city="Berlin",
        currency_code="EUR",
    )
    manufacturer = services["party_service"].create_party(
        party_code="MFR-001",
        party_name="Rotor Works GmbH",
        party_type=PartyType.MANUFACTURER,
        city="Hamburg",
        country="DE",
    )
    supplier = services["party_service"].create_party(
        party_code="SUP-001",
        party_name="Field Supply GmbH",
        party_type=PartyType.SUPPLIER,
        city="Munich",
        country="DE",
    )
    return site, manufacturer, supplier


def _build_assets_api(services):
    return build_maintenance_assets_desktop_api(
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
        site_service=services["site_service"],
        party_service=services["party_service"],
    )


def _build_preventive_api(services):
    return build_maintenance_preventive_desktop_api(
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


def test_maintenance_preventive_desktop_api_exposes_queue_library_and_templates(
    services,
) -> None:
    api = _build_preventive_api(services)
    site, manufacturer, supplier = _create_shared_maintenance_references(services)
    assets_api = _build_assets_api(services)

    location = assets_api.create_location(
        MaintenanceLocationCreateCommand(
            site_id=site.id,
            location_code="LOC-PREV",
            name="Preventive Area",
            location_type="PRODUCTION",
        )
    )
    system = assets_api.create_system(
        MaintenanceSystemCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_code="SYS-PREV",
            name="Preventive Line",
            system_type="LINE",
        )
    )
    asset = assets_api.create_asset(
        MaintenanceAssetCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_id=system.id,
            asset_code="AST-PREV",
            name="Preventive Pump",
            manufacturer_party_id=manufacturer.id,
            supplier_party_id=supplier.id,
        )
    )
    sensor = services["maintenance_sensor_service"].create_sensor(
        site_id=site.id,
        asset_id=asset.id,
        system_id=system.id,
        sensor_code="RUN-HRS-001",
        sensor_name="Run Hours",
        sensor_type="running_hours",
        source_type="manual",
        unit="H",
    )
    task_template = api.create_task_template(
        MaintenanceTaskTemplateCreateCommand(
            task_template_code="PM-QML-TPL",
            name="Monthly seal inspection",
            maintenance_type="PREVENTIVE",
            template_status="ACTIVE",
            estimated_minutes=45,
        )
    )
    plan = api.create_preventive_plan(
        MaintenancePreventivePlanCreateCommand(
            site_id=site.id,
            plan_code="PM-QML-PLAN",
            name="Monthly seal route",
            asset_id=asset.id,
            system_id=system.id,
            plan_type="PREVENTIVE",
            priority="HIGH",
            trigger_mode="SENSOR",
            sensor_id=sensor.id,
            sensor_threshold="1200",
            sensor_direction="GREATER_OR_EQUAL",
            generation_horizon_count=3,
            generation_lead_value=2,
            generation_lead_unit="DAYS",
            auto_generate_work_order=True,
            status="ACTIVE",
        )
    )
    plan_task = api.create_plan_task(
        MaintenancePreventivePlanTaskCreateCommand(
            plan_id=plan.id,
            task_template_id=task_template.id,
            sequence_no=1,
            trigger_scope="INHERIT_PLAN",
            estimated_minutes_override=50,
        )
    )

    plans = api.list_preventive_plans(site_id=site.id)
    tasks = api.list_plan_tasks(plan_id=plan.id)
    templates = api.list_task_templates(active_only=None)
    queue_rows = api.list_due_candidates(site_id=site.id)

    assert isinstance(api, MaintenancePreventiveDesktopApi)
    assert plans[0].plan_code == "PM-QML-PLAN"
    assert plans[0].sensor_label == "RUN-HRS-001 - Run Hours"
    assert tasks[0].id == plan_task.id
    assert tasks[0].task_template_label == "PM-QML-TPL - Monthly seal inspection"
    assert templates[0].task_template_code == "PM-QML-TPL"
    assert queue_rows[0].plan_id == plan.id
    assert api.list_task_template_statuses()[0].value == "DRAFT"
    assert api.list_plan_task_trigger_scopes()[0].value == "INHERIT_PLAN"
