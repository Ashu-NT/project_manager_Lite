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


def test_organization_provisioning_seeds_requested_modules_without_changing_default_org(services):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]
    module_catalog = services["module_catalog_service"]

    default_organization = organization_service.get_active_organization()
    assert default_organization.organization_code == "DEFAULT"
    assert module_catalog.is_enabled("project_management") is True

    created = app_service.provision_organization(
        organization_code="EMPTY",
        display_name="Empty Module Org",
        timezone_name="UTC",
        base_currency="EUR",
        is_active=False,
        initial_module_codes=[],
    )

    assert created.organization_code == "EMPTY"
    assert organization_service.get_active_organization().organization_code == "DEFAULT"
    assert module_catalog.is_enabled("project_management") is True

    organization_service.set_active_organization(created.id)
    assert module_catalog.current_context_label() == "Empty Module Org"
    assert module_catalog.is_enabled("project_management") is False
