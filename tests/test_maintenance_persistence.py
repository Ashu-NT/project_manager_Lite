from __future__ import annotations

from datetime import date

from core.platform.common.exceptions import ValidationError


def test_maintenance_services_persist_locations_systems_and_assets_via_service_graph(services):
    site = services["site_service"].create_site(
        site_code="MNT-PLANT",
        name="Maintenance Plant",
        city="Berlin",
    )
    manufacturer = services["party_service"].create_party(
        party_code="MFG-PLANT",
        party_name="Maintenance Maker",
        party_type="MANUFACTURER",
    )
    supplier = services["party_service"].create_party(
        party_code="SUP-PLANT",
        party_name="Maintenance Supplier",
        party_type="SUPPLIER",
    )

    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="boiler-house",
        name="Boiler House",
        location_type="AREA",
    )
    reloaded_location = services["maintenance_location_service"].find_location_by_code("BOILER-HOUSE")

    system = services["maintenance_system_service"].create_system(
        site_id=site.id,
        system_code="steam-main",
        name="Steam Main",
        location_id=location.id,
        system_type="UTILITY",
    )
    reloaded_system = services["maintenance_system_service"].find_system_by_code("STEAM-MAIN")
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="pump-100",
        name="Feed Pump 100",
        system_id=system.id,
        asset_type="PUMP",
        asset_category="ROTATING",
        manufacturer_party_id=manufacturer.id,
        supplier_party_id=supplier.id,
        install_date=date(2024, 1, 10),
        commission_date=date(2024, 1, 12),
        expected_life_years=10,
        replacement_cost="22000.00",
        maintenance_strategy="PM",
        service_level="HIGH",
        requires_shutdown_for_major_work=True,
    )
    reloaded_asset = services["maintenance_asset_service"].find_asset_by_code("PUMP-100")

    assert reloaded_location is not None
    assert reloaded_location.id == location.id
    assert reloaded_location.location_code == "BOILER-HOUSE"
    assert reloaded_location.version == 1
    assert reloaded_system is not None
    assert reloaded_system.id == system.id
    assert reloaded_system.location_id == location.id
    assert reloaded_system.system_code == "STEAM-MAIN"
    assert reloaded_asset is not None
    assert reloaded_asset.id == asset.id
    assert reloaded_asset.system_id == system.id
    assert reloaded_asset.location_id == location.id
    assert reloaded_asset.asset_code == "PUMP-100"
    assert reloaded_asset.requires_shutdown_for_major_work is True


def test_maintenance_services_use_persistent_versioned_updates(services):
    site = services["site_service"].create_site(
        site_code="MNT-UPD",
        name="Update Plant",
    )
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="shop-1",
        name="Workshop 1",
    )
    manufacturer = services["party_service"].create_party(
        party_code="MFG-UPD",
        party_name="Update Maker",
        party_type="MANUFACTURER",
    )

    updated_location = services["maintenance_location_service"].update_location(
        location.id,
        name="Workshop Alpha",
        expected_version=location.version,
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="asset-upd",
        name="Update Asset",
        manufacturer_party_id=manufacturer.id,
    )
    updated_asset = services["maintenance_asset_service"].update_asset(
        asset.id,
        name="Updated Asset Alpha",
        service_level="TIER-1",
        expected_version=asset.version,
    )

    assert updated_location.name == "Workshop Alpha"
    assert updated_location.version == location.version + 1
    assert services["maintenance_location_service"].get_location(location.id).name == "Workshop Alpha"
    assert updated_asset.name == "Updated Asset Alpha"
    assert updated_asset.service_level == "TIER-1"
    assert updated_asset.version == asset.version + 1


def test_maintenance_system_service_rejects_cross_site_persistent_location_reference(services):
    first_site = services["site_service"].create_site(site_code="MNT-A", name="Plant A")
    second_site = services["site_service"].create_site(site_code="MNT-B", name="Plant B")
    location = services["maintenance_location_service"].create_location(
        site_id=first_site.id,
        location_code="line-a",
        name="Line A",
    )

    try:
        services["maintenance_system_service"].create_system(
            site_id=second_site.id,
            system_code="bad-system",
            name="Bad System",
            location_id=location.id,
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_SYSTEM_SITE_MISMATCH"
    else:
        raise AssertionError("Expected maintenance system site mismatch validation error.")


def test_maintenance_asset_service_rejects_cross_site_persistent_system_reference(services):
    first_site = services["site_service"].create_site(site_code="MA-A", name="Plant A")
    second_site = services["site_service"].create_site(site_code="MA-B", name="Plant B")
    location_a = services["maintenance_location_service"].create_location(
        site_id=first_site.id,
        location_code="line-a",
        name="Line A",
    )
    location_b = services["maintenance_location_service"].create_location(
        site_id=second_site.id,
        location_code="line-b",
        name="Line B",
    )
    system_b = services["maintenance_system_service"].create_system(
        site_id=second_site.id,
        system_code="sys-b",
        name="System B",
        location_id=location_b.id,
    )

    try:
        services["maintenance_asset_service"].create_asset(
            site_id=first_site.id,
            location_id=location_a.id,
            asset_code="bad-cross-site",
            name="Bad Cross Site Asset",
            system_id=system_b.id,
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_ASSET_SITE_MISMATCH"
    else:
        raise AssertionError("Expected maintenance asset site mismatch validation error.")
