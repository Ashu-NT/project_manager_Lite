from __future__ import annotations

from datetime import datetime, timezone

from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetCreateCommand,
    MaintenanceComponentCreateCommand,
    MaintenanceLocationCreateCommand,
    MaintenanceSystemCreateCommand,
    MaintenanceWorkRequestCreateCommand,
    MaintenanceWorkOrderCreateCommand,
    MaintenanceWorkOrderUpdateCommand,
    build_maintenance_assets_desktop_api,
    build_maintenance_work_orders_desktop_api,
    build_maintenance_work_requests_desktop_api,
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
