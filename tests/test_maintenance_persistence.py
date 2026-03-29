from __future__ import annotations

from core.platform.common.exceptions import ValidationError


def test_maintenance_services_persist_locations_and_systems_via_service_graph(services):
    site = services["site_service"].create_site(
        site_code="MNT-PLANT",
        name="Maintenance Plant",
        city="Berlin",
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

    assert reloaded_location is not None
    assert reloaded_location.id == location.id
    assert reloaded_location.location_code == "BOILER-HOUSE"
    assert reloaded_location.version == 1
    assert reloaded_system is not None
    assert reloaded_system.id == system.id
    assert reloaded_system.location_id == location.id
    assert reloaded_system.system_code == "STEAM-MAIN"


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

    updated_location = services["maintenance_location_service"].update_location(
        location.id,
        name="Workshop Alpha",
        expected_version=location.version,
    )

    assert updated_location.name == "Workshop Alpha"
    assert updated_location.version == location.version + 1
    assert services["maintenance_location_service"].get_location(location.id).name == "Workshop Alpha"


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
