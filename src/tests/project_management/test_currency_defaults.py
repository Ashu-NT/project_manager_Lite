def _set_active_organization_currency(services, currency_code: str) -> None:
    organization_service = services["organization_service"]
    organization = organization_service.get_active_organization()
    organization_service.update_organization(
        organization.id,
        expected_version=organization.version,
        base_currency=currency_code,
    )


def test_project_defaults_currency_to_active_organization(services):
    _set_active_organization_currency(services, "USD")
    ps = services["project_service"]
    project = ps.create_project("Currency Default Project", "")
    profile = services["financial_configuration_service"].get_profile(project.id)
    assert profile.currency_code == "USD"


def test_resource_defaults_currency_to_active_organization(services):
    _set_active_organization_currency(services, "USD")
    rs = services["resource_service"]
    resource = rs.create_resource("Currency Default Resource", role="Engineer")
    assert resource.currency_code == "USD"


def test_project_resource_defaults_currency_to_project(services):
    _set_active_organization_currency(services, "USD")
    ps = services["project_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]

    project = ps.create_project(
        "Currency Default PR Project", "", financial_currency_code="GBP"
    )
    resource = rs.create_resource("Currency Default PR Resource")

    pr = prs.add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        hourly_rate=80.0,
        planned_hours=20.0,
    )
    assert pr.currency_code == "GBP"



