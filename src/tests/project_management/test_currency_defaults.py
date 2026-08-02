from src.core.modules.project_management.domain.enums import CostType


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
    assert project.currency == "USD"


def test_resource_defaults_currency_to_active_organization(services):
    _set_active_organization_currency(services, "USD")
    rs = services["resource_service"]
    resource = rs.create_resource("Currency Default Resource", role="Engineer")
    assert resource.currency_code == "USD"


def test_cost_item_defaults_currency_to_project(services):
    _set_active_organization_currency(services, "USD")
    ps = services["project_service"]
    cs = services["cost_service"]

    project = ps.create_project("Currency Default Cost Project", "", currency="GBP")
    item = cs.add_cost_item(
        project_id=project.id,
        description="Default currency item",
        planned_amount=100.0,
        cost_type=CostType.OVERHEAD,
    )
    assert item.currency_code == "GBP"


def test_project_resource_defaults_currency_to_project(services):
    _set_active_organization_currency(services, "USD")
    ps = services["project_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]

    project = ps.create_project("Currency Default PR Project", "", currency="GBP")
    resource = rs.create_resource("Currency Default PR Resource")

    pr = prs.add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        hourly_rate=80.0,
        planned_hours=20.0,
    )
    assert pr.currency_code == "GBP"


def test_explicit_transaction_currency_has_highest_precedence(services):
    _set_active_organization_currency(services, "USD")
    project = services["project_service"].create_project(
        "Currency Override Project",
        currency="GBP",
    )

    item = services["cost_service"].add_cost_item(
        project_id=project.id,
        description="Explicit currency item",
        planned_amount=100.0,
        currency_code="CAD",
    )

    assert item.currency_code == "CAD"

