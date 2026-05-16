from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.api.desktop.runtime import build_desktop_api_registry
from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetCreateCommand,
    MaintenanceComponentCreateCommand,
    MaintenanceDashboardSnapshotDescriptor,
    MaintenanceLocationCreateCommand,
    MaintenanceLocationUpdateCommand,
    MaintenancePlannerSnapshotDescriptor,
    MaintenancePreventiveDesktopApi,
    MaintenancePreventivePlanCreateCommand,
    MaintenancePreventivePlanTaskCreateCommand,
    MaintenanceTaskTemplateCreateCommand,
    MaintenanceReliabilitySnapshotDescriptor,
    MaintenanceSystemCreateCommand,
    MaintenanceAssetUpdateCommand,
    MaintenanceWorkRequestCreateCommand,
    MaintenanceWorkOrderCreateCommand,
    MaintenanceWorkOrderUpdateCommand,
    MaintenanceWorkRequestUpdateCommand,
    build_maintenance_assets_desktop_api,
    build_maintenance_dashboard_desktop_api,
    build_maintenance_planner_desktop_api,
    build_maintenance_preventive_desktop_api,
    build_maintenance_reliability_desktop_api,
    build_maintenance_work_orders_desktop_api,
    build_maintenance_work_requests_desktop_api,
    build_maintenance_workspace_desktop_api,
)
from src.core.platform.party.domain import PartyType


EXPECTED_MAINTENANCE_WORKSPACE_KEYS = [
    "dashboard",
    "assets",
    "work_requests",
    "work_orders",
    "preventive",
    "reliability",
    "planner",
]


def test_maintenance_desktop_api_lists_workspace_descriptors() -> None:
    api = build_maintenance_workspace_desktop_api()

    descriptors = api.list_workspaces()

    assert [descriptor.key for descriptor in descriptors] == EXPECTED_MAINTENANCE_WORKSPACE_KEYS
    assert descriptors[1].title == "Assets"
    assert api.get_workspace("maintenance_management.work_orders").title == "Work Orders"
    assert api.get_workspace("maintenance_management.unknown") is None


def test_build_desktop_api_registry_exposes_maintenance_adapters(services) -> None:
    registry = build_desktop_api_registry(services)

    assert registry.maintenance_workspaces.list_workspaces()[0].key == "dashboard"
    assert registry.maintenance_workspaces.get_workspace("maintenance_management.planner").title == "Planner"
    assert registry.maintenance_assets.list_lifecycle_statuses()[0].value == "DRAFT"
    assert registry.maintenance_dashboard.build_snapshot().overview.title == "Maintenance Dashboard"
    assert registry.maintenance_planner.build_snapshot().overview.title == "Planner"
    assert registry.maintenance_preventive.list_plan_types()[0].value == "PREVENTIVE"
    assert registry.maintenance_reliability.build_snapshot().overview.title == "Reliability"
    assert registry.maintenance_work_requests.list_statuses()[0].value == "NEW"
    assert registry.maintenance_work_orders.list_statuses()[0].value == "DRAFT"


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


def _build_dashboard_api(services):
    return build_maintenance_dashboard_desktop_api(
        reliability_service=services["maintenance_reliability_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
    )


def _build_reliability_api(services):
    return build_maintenance_reliability_desktop_api(
        reliability_service=services["maintenance_reliability_service"],
        failure_code_service=services["maintenance_failure_code_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
    )


def _create_maintenance_reliability_context(services):
    site, manufacturer, supplier = _create_shared_maintenance_references(services)
    assets_api = _build_assets_api(services)
    work_orders_api = _build_work_orders_api(services)
    now = datetime.now(timezone.utc)

    location = assets_api.create_location(
        MaintenanceLocationCreateCommand(
            site_id=site.id,
            location_code="LOC-REL",
            name="Reliability Area",
            location_type="PRODUCTION",
        )
    )
    system = assets_api.create_system(
        MaintenanceSystemCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_code="SYS-REL",
            name="Reliability Line",
            system_type="LINE",
        )
    )
    asset = assets_api.create_asset(
        MaintenanceAssetCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_id=system.id,
            asset_code="AST-REL",
            name="Pump 501",
            manufacturer_party_id=manufacturer.id,
            supplier_party_id=supplier.id,
        )
    )
    open_order = work_orders_api.create_work_order(
        MaintenanceWorkOrderCreateCommand(
            site_id=site.id,
            work_order_code="WO-REL-OPEN",
            work_order_type="CORRECTIVE",
            asset_id=asset.id,
            system_id=system.id,
            location_id=location.id,
            title="Open backlog repair",
            description="Still waiting in the active backlog.",
            priority="HIGH",
        )
    )
    open_order = work_orders_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=open_order.id,
            status="PLANNED",
            expected_version=open_order.version,
        )
    )
    symptom = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="REL-SYM-001",
        name="Seal Leak",
        code_type="symptom",
    )
    cause = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="REL-CAUSE-001",
        name="Misalignment",
        code_type="cause",
    )

    completed_orders = []
    for index, downtime_minutes in enumerate((45, 60), start=1):
        row = work_orders_api.create_work_order(
            MaintenanceWorkOrderCreateCommand(
                site_id=site.id,
                work_order_code=f"WO-REL-{index:03d}",
                work_order_type="CORRECTIVE",
                asset_id=asset.id,
                system_id=system.id,
                location_id=location.id,
                title=f"Recurring repair {index}",
                description="Recurring reliability repair.",
                priority="MEDIUM",
            )
        )
        row = work_orders_api.update_work_order(
            MaintenanceWorkOrderUpdateCommand(
                work_order_id=row.id,
                status="PLANNED",
                expected_version=row.version,
            )
        )
        row = work_orders_api.update_work_order(
            MaintenanceWorkOrderUpdateCommand(
                work_order_id=row.id,
                status="RELEASED",
                expected_version=row.version,
            )
        )
        row = work_orders_api.update_work_order(
            MaintenanceWorkOrderUpdateCommand(
                work_order_id=row.id,
                status="IN_PROGRESS",
                expected_version=row.version,
            )
        )
        row = work_orders_api.update_work_order(
            MaintenanceWorkOrderUpdateCommand(
                work_order_id=row.id,
                status="COMPLETED",
                failure_code=symptom.failure_code,
                root_cause_code=cause.failure_code,
                downtime_minutes=downtime_minutes,
                expected_version=row.version,
            )
        )
        services["maintenance_downtime_event_service"].create_downtime_event(
            work_order_id=row.id,
            started_at=(now - timedelta(days=index, hours=2)).isoformat(),
            ended_at=(now - timedelta(days=index, hours=1)).isoformat(),
            downtime_type="UNPLANNED",
            reason_code=symptom.failure_code,
            impact_notes=f"Recurring leak event {index}.",
        )
        completed_orders.append(row)

    return {
        "site": site,
        "location": location,
        "system": system,
        "asset": asset,
        "symptom": symptom,
        "cause": cause,
        "open_order": open_order,
        "completed_orders": tuple(completed_orders),
    }


def test_maintenance_assets_desktop_api_mutates_asset_scope_records(services) -> None:
    site, manufacturer, supplier = _create_shared_maintenance_references(services)
    api = _build_assets_api(services)

    location = api.create_location(
        MaintenanceLocationCreateCommand(
            site_id=site.id,
            location_code="LOC-A",
            name="Area A",
            location_type="PRODUCTION",
            criticality="HIGH",
        )
    )
    updated_location = api.update_location(
        MaintenanceLocationUpdateCommand(
            location_id=location.id,
            name="Area A1",
            expected_version=location.version,
        )
    )
    system = api.create_system(
        MaintenanceSystemCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_code="SYS-PACK",
            name="Packaging Line",
            system_type="LINE",
            criticality="HIGH",
        )
    )
    asset = api.create_asset(
        MaintenanceAssetCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_id=system.id,
            asset_code="AST-100",
            name="Conveyor 100",
            asset_type="CONVEYOR",
            asset_category="ROTATING",
            manufacturer_party_id=manufacturer.id,
            supplier_party_id=supplier.id,
            replacement_cost=2500.0,
            install_date="2026-01-10",
            warranty_end="2027-01-10",
        )
    )
    updated_asset = api.update_asset(
        MaintenanceAssetUpdateCommand(
            asset_id=asset.id,
            name="Conveyor 100 Rev A",
            replacement_cost=2750.0,
            expected_version=asset.version,
        )
    )
    component = api.create_component(
        MaintenanceComponentCreateCommand(
            asset_id=asset.id,
            component_code="CMP-MTR",
            name="Drive Motor",
            component_type="MOTOR",
            manufacturer_party_id=manufacturer.id,
            supplier_party_id=supplier.id,
            expected_life_hours=12000,
            is_critical_component=True,
        )
    )

    locations = api.list_locations(active_only=None)
    systems = api.list_systems(active_only=None)
    assets = api.list_assets(active_only=None)
    components = api.list_components(active_only=None)

    assert updated_location.name == "Area A1"
    assert system.location_label == "LOC-A - Area A1"
    assert asset.site_label == "MNT-HQ - Maintenance HQ"
    assert asset.manufacturer_party_label == "MFR-001 - Rotor Works GmbH"
    assert updated_asset.name == "Conveyor 100 Rev A"
    assert updated_asset.replacement_cost == 2750.0
    assert component.asset_label == "AST-100 - Conveyor 100 Rev A"
    assert component.is_critical_component is True
    assert locations[0].location_code == "LOC-A"
    assert systems[0].system_code == "SYS-PACK"
    assert assets[0].asset_code == "AST-100"
    assert components[0].component_code == "CMP-MTR"
    assert any(
        option.value == manufacturer.id
        for option in api.list_manufacturer_parties(active_only=True)
    )
    assert any(
        option.value == supplier.id
        for option in api.list_supplier_parties(active_only=True)
    )
    assert api.list_asset_options(active_only=None)[0].label == "AST-100 - Conveyor 100 Rev A"
    assert api.list_component_options(active_only=None)[0].label == "CMP-MTR - Drive Motor"


def test_maintenance_work_requests_desktop_api_mutates_request_records(services) -> None:
    site, manufacturer, supplier = _create_shared_maintenance_references(services)
    assets_api = _build_assets_api(services)
    api = _build_work_requests_api(services)

    location = assets_api.create_location(
        MaintenanceLocationCreateCommand(
            site_id=site.id,
            location_code="LOC-WR",
            name="Request Area",
            location_type="UTILITY",
        )
    )
    system = assets_api.create_system(
        MaintenanceSystemCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_code="SYS-WR",
            name="Cooling Loop",
            system_type="UTILITY",
        )
    )
    asset = assets_api.create_asset(
        MaintenanceAssetCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_id=system.id,
            asset_code="AST-WR",
            name="Pump 12",
            manufacturer_party_id=manufacturer.id,
            supplier_party_id=supplier.id,
        )
    )
    component = assets_api.create_component(
        MaintenanceComponentCreateCommand(
            asset_id=asset.id,
            component_code="CMP-WR",
            name="Seal Cartridge",
            supplier_party_id=supplier.id,
        )
    )

    work_request = api.create_work_request(
        MaintenanceWorkRequestCreateCommand(
            site_id=site.id,
            work_request_code="WR-100",
            source_type="MANUAL",
            request_type="CORRECTIVE",
            asset_id=asset.id,
            component_id=component.id,
            system_id=system.id,
            location_id=location.id,
            title="Seal leak observed",
            description="Investigate and stop the leak.",
            priority="HIGH",
            safety_risk_level="MEDIUM",
            production_impact_level="HIGH",
        )
    )
    updated_work_request = api.update_work_request(
        MaintenanceWorkRequestUpdateCommand(
            work_request_id=work_request.id,
            status="TRIAGED",
            notes="Escalated to planning.",
            expected_version=work_request.version,
        )
    )
    requests = api.list_work_requests(site_id=site.id)

    assert work_request.asset_label == "AST-WR - Pump 12"
    assert work_request.component_label == "CMP-WR - Seal Cartridge"
    assert work_request.priority_label == "High"
    assert updated_work_request.status == "TRIAGED"
    assert updated_work_request.status_label == "Triaged"
    assert updated_work_request.notes == "Escalated to planning."
    assert updated_work_request.triaged_at != ""
    assert requests[0].work_request_code == "WR-100"
    assert api.list_source_types()[0].value == "MANUAL"
    assert api.list_priorities()[-1].value == "EMERGENCY"
    assert any(option.value == asset.id for option in api.list_asset_options(active_only=None))
    assert any(option.value == component.id for option in api.list_component_options(active_only=None))


def test_maintenance_work_orders_desktop_api_mutates_work_order_records(services) -> None:
    site, manufacturer, supplier = _create_shared_maintenance_references(services)
    assets_api = _build_assets_api(services)
    work_requests_api = _build_work_requests_api(services)
    api = _build_work_orders_api(services)
    assigned_employee = services["employee_service"].create_employee(
        employee_code="EMP-MNT-01",
        full_name="Rita Planner",
        site_id=site.id,
    )

    location = assets_api.create_location(
        MaintenanceLocationCreateCommand(
            site_id=site.id,
            location_code="LOC-WO",
            name="Work Order Zone",
            location_type="PRODUCTION",
        )
    )
    system = assets_api.create_system(
        MaintenanceSystemCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_code="SYS-WO",
            name="Filling Line",
            system_type="LINE",
        )
    )
    asset = assets_api.create_asset(
        MaintenanceAssetCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_id=system.id,
            asset_code="AST-WO",
            name="Mixer 7",
            manufacturer_party_id=manufacturer.id,
            supplier_party_id=supplier.id,
        )
    )
    component = assets_api.create_component(
        MaintenanceComponentCreateCommand(
            asset_id=asset.id,
            component_code="CMP-WO",
            name="Drive Coupling",
            supplier_party_id=supplier.id,
        )
    )
    work_request = work_requests_api.create_work_request(
        MaintenanceWorkRequestCreateCommand(
            site_id=site.id,
            work_request_code="WR-200",
            source_type="MANUAL",
            request_type="CORRECTIVE",
            asset_id=asset.id,
            component_id=component.id,
            system_id=system.id,
            location_id=location.id,
            title="Coupling vibration alarm",
            description="Inspect coupling alignment and wear.",
            priority="HIGH",
        )
    )

    source_options = api.list_source_work_request_options(site_id=site.id)
    work_order = api.create_work_order(
        MaintenanceWorkOrderCreateCommand(
            site_id=site.id,
            work_order_code="WO-200",
            work_order_type="CORRECTIVE",
            source_type="WORK_REQUEST",
            source_id=work_request.id,
            asset_id=asset.id,
            component_id=component.id,
            system_id=system.id,
            location_id=location.id,
            title="Repair coupling",
            description="Repair the coupling and verify alignment.",
            priority="HIGH",
            vendor_party_id=supplier.id,
            requires_shutdown=True,
            approval_required=True,
        )
    )
    updated_work_order = api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=work_order.id,
            status="PLANNED",
            assigned_employee_id=assigned_employee.id,
            planned_start=datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc).isoformat(),
            planned_end=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
            labor_cost=320.5,
            parts_cost=120.25,
            expected_version=work_order.version,
        )
    )
    work_orders = api.list_work_orders(site_id=site.id)
    remaining_source_options = api.list_source_work_request_options(site_id=site.id)

    assert source_options[0].value == work_request.id
    assert work_order.source_label == "WR-200 - Coupling vibration alarm"
    assert work_order.component_label == "CMP-WO - Drive Coupling"
    assert work_order.vendor_party_label == "SUP-001 - Field Supply GmbH"
    assert updated_work_order.status == "PLANNED"
    assert updated_work_order.status_label == "Planned"
    assert updated_work_order.assigned_employee_id == assigned_employee.id
    assert updated_work_order.assigned_employee_label == "EMP-MNT-01 - Rita Planner"
    assert updated_work_order.planned_start.startswith("2026-05-01T08:00:00")
    assert updated_work_order.labor_cost == 320.5
    assert updated_work_order.parts_cost == 120.25
    assert work_orders[0].work_order_code == "WO-200"
    assert api.list_work_order_types()[0].value == "CORRECTIVE"
    assert api.list_vendor_parties(active_only=True)[0].value == supplier.id
    assert any(option.value == assigned_employee.id for option in api.list_employee_options(site_id=site.id))
    assert all(option.value != work_request.id for option in remaining_source_options)


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
    recurring_one = work_orders_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=recurring_one.id,
            status="PLANNED",
            expected_version=recurring_one.version,
        )
    )
    recurring_one = work_orders_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=recurring_one.id,
            status="RELEASED",
            expected_version=recurring_one.version,
        )
    )
    recurring_one = work_orders_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=recurring_one.id,
            status="IN_PROGRESS",
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
    recurring_two = work_orders_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=recurring_two.id,
            status="PLANNED",
            expected_version=recurring_two.version,
        )
    )
    recurring_two = work_orders_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=recurring_two.id,
            status="RELEASED",
            expected_version=recurring_two.version,
        )
    )
    recurring_two = work_orders_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=recurring_two.id,
            status="IN_PROGRESS",
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


def test_maintenance_dashboard_desktop_api_builds_reliability_snapshot(services) -> None:
    api = _build_dashboard_api(services)
    context = _create_maintenance_reliability_context(services)

    snapshot = api.build_snapshot(
        site_id=context["site"].id,
        asset_id=context["asset"].id,
        system_id=context["system"].id,
        location_id=context["location"].id,
        days=90,
    )

    assert isinstance(snapshot, MaintenanceDashboardSnapshotDescriptor)
    assert snapshot.overview.title == "Maintenance Dashboard"
    metrics = {metric.label: metric.value for metric in snapshot.overview.metrics}
    assert metrics["Open work orders"] == "1"
    assert metrics["Completed in window"] == "2"
    assert metrics["Downtime minutes"] == "120"
    assert snapshot.backlog_rows[0].label == "Planned"
    assert snapshot.root_cause_rows[0].root_cause_name == "Misalignment"
    assert snapshot.recurring_rows[0].anchor_label == "AST-REL - Pump 501"


def test_maintenance_reliability_desktop_api_builds_analysis_snapshot(services) -> None:
    api = _build_reliability_api(services)
    context = _create_maintenance_reliability_context(services)

    snapshot = api.build_snapshot(
        site_id=context["site"].id,
        asset_id=context["asset"].id,
        system_id=context["system"].id,
        location_id=context["location"].id,
        failure_code=context["symptom"].failure_code,
        days=90,
        limit=20,
        threshold=2,
    )

    assert isinstance(snapshot, MaintenanceReliabilitySnapshotDescriptor)
    assert snapshot.overview.title == "Reliability"
    metrics = {metric.label: metric.value for metric in snapshot.overview.metrics}
    assert metrics["Suggestions"] == "1"
    assert metrics["Root causes"] == "1"
    assert metrics["Recurring patterns"] == "1"
    assert snapshot.suggestion_rows[0].root_cause_name == "Misalignment"
    assert snapshot.root_cause_rows[0].failure_name == "Seal Leak"
    assert snapshot.recurring_rows[0].anchor_label == "AST-REL - Pump 501"


def test_maintenance_desktop_api_does_not_import_qml_or_legacy_ui() -> None:
    root = Path("src/core/modules/maintenance/api/desktop")
    combined = "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.py")))

    assert "src.ui_qml" not in combined
    assert "ui.modules.maintenance_management" not in combined
