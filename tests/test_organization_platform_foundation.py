from __future__ import annotations


def test_organization_service_bootstraps_default_and_switches_active_context(services):
    organization_service = services["organization_service"]

    initial_rows = organization_service.list_organizations()
    assert len(initial_rows) == 1
    assert initial_rows[0].organization_code == "DEFAULT"
    assert initial_rows[0].is_active is True

    second = organization_service.create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )

    rows = organization_service.list_organizations()
    assert len(rows) == 2
    assert organization_service.get_active_organization().organization_code == "DEFAULT"

    organization_service.set_active_organization(second.id)

    active = organization_service.get_active_organization()
    assert active.organization_code == "NORTH"
    status_by_code = {
        row.organization_code: row.is_active
        for row in organization_service.list_organizations()
    }
    assert status_by_code == {"DEFAULT": False, "NORTH": True}
