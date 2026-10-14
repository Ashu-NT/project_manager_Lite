from src.core.platform.application.master_data.org.dto import (
    OrganizationUpdateCommand,
)


def _set_active_organization_currency(services, currency_code: str) -> None:
    organization = services["tenant_context_service"].get_active_organization()
    services["organization_commands"].update_organization(OrganizationUpdateCommand(organization_id=organization.id, expected_version=organization.version, base_currency=currency_code))


def test_project_defaults_currency_to_active_organization(services):
    _set_active_organization_currency(services, "USD")
    ps = services['project_query']
    project = services['project_create'].create_project("Currency Default Project", "")
    profile = services['financial_configuration_query'].get_profile(project.id)
    assert profile.currency_code == "USD"


def test_resource_defaults_currency_to_active_organization(services):
    _set_active_organization_currency(services, "USD")
    resource = services["resource_master_commands"].create_resource("Currency Default Resource", role="Engineer")
    assert resource.currency_code == "USD"


def test_project_resource_defaults_currency_to_project(services):
    _set_active_organization_currency(services, "USD")
    ps = services['project_query']
    services["project_resource_query"]

    project = services['project_create'].create_project(
        "Currency Default PR Project", "", financial_currency_code="GBP"
    )
    resource = services["resource_master_commands"].create_resource("Currency Default PR Resource")

    pr = services["project_resource_commands"].add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        hourly_rate=80.0,
        planned_hours=20.0,
    )
    assert pr.currency_code == "GBP"



