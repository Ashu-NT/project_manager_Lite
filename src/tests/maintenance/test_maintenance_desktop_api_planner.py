from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetCreateCommand,
    MaintenanceLocationCreateCommand,
    MaintenancePlannerSnapshotDescriptor,
    MaintenanceSystemCreateCommand,
    MaintenanceWorkOrderCreateCommand,
    MaintenanceWorkOrderUpdateCommand,
    MaintenanceWorkRequestCreateCommand,
    build_maintenance_assets_desktop_api,
    build_maintenance_planner_desktop_api,
    build_maintenance_work_orders_desktop_api,
    build_maintenance_work_requests_desktop_api,
)
from src.core.platform.party.domain import PartyType


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


def _build_work_requests_api(services):
    return build_maintenance_work_requests_desktop_api(
        work_request_service=services["maintenance_work_request_service"],
        site_service=services["site_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
    )


def _build_work_orders_api(services):
    return build_maintenance_work_orders_desktop_api(
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


def _build_planner_api(services):
    return build_maintenance_planner_desktop_api(
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        system_service=services["maintenance_system_service"],
        work_request_service=services["maintenance_work_request_service"],
        work_order_service=services["maintenance_work_order_service"],
        material_requirement_service=services["maintenance_work_order_material_requirement_service"],
        preventive_plan_service=services["maintenance_preventive_plan_service"],
        preventive_generation_service=services["maintenance_preventive_generation_service"],
        reliability_service=services["maintenance_reliability_service"],
        sensor_exception_service=services["maintenance_sensor_exception_service"],
    )


def test_maintenance_planner_desktop_api_builds_snapshot_from_live_services(services) -> None:
    site, manufacturer, supplier = _create_shared_maintenance_references(services)
    assets_api = _build_assets_api(services)
    work_requests_api = _build_work_requests_api(services)
    work_orders_api = _build_work_orders_api(services)
    planner_api = _build_planner_api(services)

    location = assets_api.create_location(
        MaintenanceLocationCreateCommand(
            site_id=site.id,
            location_code="LOC-PLN",
            name="Planner Area",
            location_type="PRODUCTION",
        )
    )
    system = assets_api.create_system(
        MaintenanceSystemCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_code="SYS-PLN",
            name="Planner Line",
            system_type="LINE",
        )
    )
    asset = assets_api.create_asset(
        MaintenanceAssetCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_id=system.id,
            asset_code="AST-PLN",
            name="Planner Conveyor",
            manufacturer_party_id=manufacturer.id,
            supplier_party_id=supplier.id,
        )
    )
    open_request = work_requests_api.create_work_request(
        MaintenanceWorkRequestCreateCommand(
            site_id=site.id,
            work_request_code="WR-PLN-001",
            source_type="MANUAL",
            request_type="CORRECTIVE",
            asset_id=asset.id,
            system_id=system.id,
            location_id=location.id,
            title="Planner alarm triage",
            description="Needs planner review.",
            priority="HIGH",
        )
    )
    source_request = work_requests_api.create_work_request(
        MaintenanceWorkRequestCreateCommand(
            site_id=site.id,
            work_request_code="WR-PLN-SRC",
            source_type="MANUAL",
            request_type="CORRECTIVE",
            asset_id=asset.id,
            system_id=system.id,
            location_id=location.id,
            title="Planner source request",
            description="Converted into a backlog work order.",
            priority="HIGH",
        )
    )
    backlog_order = work_orders_api.create_work_order(
        MaintenanceWorkOrderCreateCommand(
            site_id=site.id,
            work_order_code="WO-PLN-001",
            work_order_type="CORRECTIVE",
            source_type="WORK_REQUEST",
            source_id=source_request.id,
            asset_id=asset.id,
            system_id=system.id,
            location_id=location.id,
            title="Backlog repair",
            description="Backlog repair waiting on planning.",
            priority="HIGH",
            vendor_party_id=supplier.id,
        )
    )
    services["maintenance_work_order_material_requirement_service"].create_requirement(
        work_order_id=backlog_order.id,
        description="Bearing grease",
        required_qty="4",
        required_uom="EA",
        is_stock_item=False,
    )
    symptom = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="PLN-SYM",
        name="Planner Vibration",
        code_type="symptom",
    )
    cause = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="PLN-CAUSE",
        name="Planner Misalignment",
        code_type="cause",
    )
    recurring_one = work_orders_api.create_work_order(
        MaintenanceWorkOrderCreateCommand(
            site_id=site.id,
            work_order_code="WO-REC-001",
            work_order_type="CORRECTIVE",
            asset_id=asset.id,
            system_id=system.id,
            location_id=location.id,
            title="Recurring repair 1",
            description="Recurring reliability repair.",
            priority="MEDIUM",
        )
    )
    for status in ("PLANNED", "RELEASED", "IN_PROGRESS"):
        recurring_one = work_orders_api.update_work_order(
            MaintenanceWorkOrderUpdateCommand(
                work_order_id=recurring_one.id,
                status=status,
                expected_version=recurring_one.version,
            )
        )
    recurring_one = work_orders_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=recurring_one.id,
            status="COMPLETED",
            failure_code=symptom.failure_code,
            root_cause_code=cause.failure_code,
            downtime_minutes=30,
            expected_version=recurring_one.version,
        )
    )
    recurring_two = work_orders_api.create_work_order(
        MaintenanceWorkOrderCreateCommand(
            site_id=site.id,
            work_order_code="WO-REC-002",
            work_order_type="CORRECTIVE",
            asset_id=asset.id,
            system_id=system.id,
            location_id=location.id,
            title="Recurring repair 2",
            description="Recurring reliability repair repeat.",
            priority="MEDIUM",
        )
    )
    for status in ("PLANNED", "RELEASED", "IN_PROGRESS"):
        recurring_two = work_orders_api.update_work_order(
            MaintenanceWorkOrderUpdateCommand(
                work_order_id=recurring_two.id,
                status=status,
                expected_version=recurring_two.version,
            )
        )
    work_orders_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=recurring_two.id,
            status="COMPLETED",
            failure_code=symptom.failure_code,
            root_cause_code=cause.failure_code,
            downtime_minutes=45,
            expected_version=recurring_two.version,
        )
    )
    task_template = services["maintenance_task_template_service"].create_task_template(
        task_template_code="PLN-TASK",
        name="Planner PM task",
        maintenance_type="preventive",
        template_status="active",
        estimated_minutes=30,
    )
    due_plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="PM-PLN-001",
        name="Planner due PM",
        asset_id=asset.id,
        plan_type="preventive",
        priority="high",
        trigger_mode="calendar",
        calendar_frequency_unit="weekly",
        calendar_frequency_value=1,
        next_due_at="2026-05-01T08:00:00+00:00",
        auto_generate_work_order=True,
        status="active",
    )
    services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=due_plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="inherit_plan",
    )

    snapshot = planner_api.build_snapshot(
        site_id=site.id,
        asset_id=asset.id,
    )

    assert isinstance(snapshot, MaintenancePlannerSnapshotDescriptor)
    assert snapshot.overview.title == "Planner"
    assert {metric.label: metric.value for metric in snapshot.overview.metrics} == {
        "Open Requests": "1",
        "Backlog Orders": "1",
        "Preventive Review": "1",
        "Material Risks": "1",
        "Recurring Patterns": "1",
    }
    assert snapshot.request_rows[0].request_label == "WR-PLN-001 - Planner alarm triage"
    assert snapshot.work_order_rows[0].work_order_label == "WO-PLN-001 - Backlog repair"
    assert snapshot.material_rows[0].material_label == "Bearing grease"
    assert snapshot.preventive_rows[0].plan_label == "PM-PLN-001 - Planner due PM"
    assert snapshot.preventive_rows[0].due_state == "DUE"
    assert snapshot.recurring_rows[0].occurrence_count == 2
    assert snapshot.recurring_rows[0].failure_name == "Planner Vibration"
