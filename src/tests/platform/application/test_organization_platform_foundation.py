from __future__ import annotations


def test_organization_service_bootstraps_default_and_activates_another_organization_independently(services):
    """Activating one organization must never deactivate a sibling -- multiple organizations in
    the same tenant may be `status == ACTIVE` simultaneously."""
    organization_service = services["organization_service"]

    initial_rows = organization_service.list_organizations()
    assert len(initial_rows) == 1
    assert initial_rows[0].organization_code == "DEFAULT"
    assert initial_rows[0].status == "active"

    second = organization_service.create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
    )
    organization_service.deactivate_organization(second.id)

    rows = organization_service.list_organizations()
    assert len(rows) == 2
    status_by_code = {row.organization_code: row.status for row in rows}
    assert status_by_code == {"DEFAULT": "active", "NORTH": "inactive"}

    organization_service.activate_organization(second.id)

    status_by_code = {
        row.organization_code: row.status
        for row in organization_service.list_organizations()
    }
    # Both organizations are active -- no mutual exclusion.
    assert status_by_code == {"DEFAULT": "active", "NORTH": "active"}


def test_organization_provisioning_seeds_requested_modules_and_switches_to_the_new_org(services):
    """New organizations are always created ACTIVE, and provisioning always switches the caller's
    session into the just-created organization."""
    app_service = services["platform_runtime_application_service"]
    tenant_context_service = services["tenant_context_service"]
    module_catalog = services["module_catalog_service"]

    default_organization = tenant_context_service.get_active_organization()
    assert default_organization.organization_code == "DEFAULT"
    assert module_catalog.is_enabled("project_management") is True

    created = app_service.provision_organization(
        organization_code="EMPTY",
        display_name="Empty Module Org",
        timezone_name="UTC",
        base_currency="EUR",
        initial_module_codes=[],
    )

    assert created.organization_code == "EMPTY"
    assert tenant_context_service.get_active_organization().organization_code == "EMPTY"
    assert module_catalog.current_context_label() == "Empty Module Org"
    assert module_catalog.is_enabled("project_management") is False
