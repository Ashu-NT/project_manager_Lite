from __future__ import annotations

def test_module_entitlements_are_scoped_by_active_organization(services):
    organization_service = services["organization_service"]
    module_catalog = services["module_catalog_service"]

    default_organization = organization_service.get_active_organization()
    second_organization = organization_service.create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )

    assert module_catalog.is_enabled("project_management") is True

    organization_service.set_active_organization(second_organization.id)
    assert module_catalog.is_enabled("project_management") is True

    module_catalog.set_module_state("project_management", enabled=False)
    assert module_catalog.is_enabled("project_management") is False

    organization_service.set_active_organization(default_organization.id)
    assert module_catalog.current_context_label() == "Default Organization"
    assert module_catalog.is_enabled("project_management") is True

    organization_service.set_active_organization(second_organization.id)
    assert module_catalog.current_context_label() == "North Division"
    assert module_catalog.is_enabled("project_management") is False
