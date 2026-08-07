from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetCreateCommand,
    MaintenanceAssetUpdateCommand,
    MaintenanceComponentCreateCommand,
    MaintenanceLocationCreateCommand,
    MaintenanceLocationUpdateCommand,
    MaintenanceSystemCreateCommand,
    build_maintenance_assets_desktop_api,
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
