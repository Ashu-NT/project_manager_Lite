from __future__ import annotations


def test_organization_service_bootstraps_default_and_enables_another_organization_independently(services):
    """P10A: enabling one organization must never disable a sibling -- multiple organizations in
    the same tenant may be is_enabled=True simultaneously."""
    organization_service = services["organization_service"]

    initial_rows = organization_service.list_organizations()
    assert len(initial_rows) == 1
    assert initial_rows[0].organization_code == "DEFAULT"
    assert initial_rows[0].is_enabled is True

    second = organization_service.create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_enabled=False,
    )

    rows = organization_service.list_organizations()
    assert len(rows) == 2
    status_by_code = {row.organization_code: row.is_enabled for row in rows}
    assert status_by_code == {"DEFAULT": True, "NORTH": False}

    organization_service.enable_organization(second.id)

    status_by_code = {
        row.organization_code: row.is_enabled
        for row in organization_service.list_organizations()
    }
    # Both organizations are enabled -- no mutual exclusion, unlike the pre-P10A model.
    assert status_by_code == {"DEFAULT": True, "NORTH": True}


def test_organization_provisioning_seeds_requested_modules_without_changing_default_org(services):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]
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
        is_enabled=False,
        initial_module_codes=[],
    )

    assert created.organization_code == "EMPTY"
    assert tenant_context_service.get_active_organization().organization_code == "DEFAULT"
    assert module_catalog.is_enabled("project_management") is True

    # P10A: enabling and session-selecting are two separate, explicit steps -- enabling alone
    # (organization availability) never switches anyone's current working organization.
    organization_service.enable_organization(created.id)
    assert tenant_context_service.get_active_organization().organization_code == "DEFAULT"

    tenant_context_service.set_active_organization(created.id)
    assert module_catalog.current_context_label() == "Empty Module Org"
    assert module_catalog.is_enabled("project_management") is False
