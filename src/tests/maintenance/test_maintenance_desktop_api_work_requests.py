from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetCreateCommand,
    MaintenanceComponentCreateCommand,
    MaintenanceLocationCreateCommand,
    MaintenanceSystemCreateCommand,
    MaintenanceWorkRequestCreateCommand,
    MaintenanceWorkRequestUpdateCommand,
    build_maintenance_assets_desktop_api,
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
