from __future__ import annotations

from core.platform.common.exceptions import ValidationError


def test_site_service_scopes_site_master_data_by_active_organization(services):
    organization_service = services["organization_service"]
    site_service = services["site_service"]

    default_organization = organization_service.get_active_organization()
    created = site_service.create_site(site_code="HQ", display_name="Headquarters")

    assert created.organization_id == default_organization.id
    assert [site.display_name for site in site_service.list_sites()] == ["Headquarters"]

    second_organization = organization_service.create_organization(
        organization_code="OPS",
        display_name="Operations Hub",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )
    organization_service.set_active_organization(second_organization.id)

    assert site_service.get_context_organization().display_name == "Operations Hub"
    assert site_service.list_sites() == []

    plant = site_service.create_site(site_code="PLANT1", display_name="Plant 1")
    assert plant.organization_id == second_organization.id
    assert [site.site_code for site in site_service.list_sites()] == ["PLANT1"]

    organization_service.set_active_organization(default_organization.id)
    assert site_service.get_context_organization().display_name == "Default Organization"
    assert [site.site_code for site in site_service.list_sites()] == ["HQ"]


def test_site_service_rejects_duplicate_codes_inside_one_organization(services):
    site_service = services["site_service"]

    site_service.create_site(site_code="HQ", display_name="Headquarters")

    try:
        site_service.create_site(site_code="HQ", display_name="Second HQ")
    except ValidationError as exc:
        assert exc.code == "SITE_CODE_EXISTS"
    else:
        raise AssertionError("Expected duplicate site code validation error.")


def test_site_service_updates_site_metadata(services):
    site_service = services["site_service"]
    created = site_service.create_site(site_code="YARD", display_name="Yard")

    updated = site_service.update_site(
        created.id,
        display_name="North Yard",
        is_active=False,
        expected_version=created.version,
    )

    assert updated.display_name == "North Yard"
    assert updated.is_active is False
    assert [site.display_name for site in site_service.list_sites(active_only=False)] == ["North Yard"]
