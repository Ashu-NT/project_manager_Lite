from __future__ import annotations


def test_module_entitlements_are_scoped_by_active_organization(services):
    module_catalog = services["module_catalog_service"]

    default_organization = services["tenant_context_service"].get_active_organization()
    second_organization = services["organization_commands"].create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
    )

    assert module_catalog.is_enabled("project_management") is True

    services["tenant_context_service"].set_active_organization(second_organization.id)
    assert module_catalog.is_enabled("project_management") is True

    services["module_entitlement_commands"].disable_module(second_organization.id, "project_management")
    assert module_catalog.is_enabled("project_management") is False

    services["tenant_context_service"].set_active_organization(default_organization.id)
    assert module_catalog.current_context_label() == "Default Organization"
    assert module_catalog.is_enabled("project_management") is True

    services["tenant_context_service"].set_active_organization(second_organization.id)
    assert module_catalog.current_context_label() == "North Division"
    assert module_catalog.is_enabled("project_management") is False

