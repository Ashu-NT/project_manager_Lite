from core.models import CostType


def test_project_defaults_currency_to_eur(services):
    ps = services["project_service"]
    project = ps.create_project("Currency Default Project", "")
    assert project.currency == "EUR"


def test_resource_defaults_currency_to_eur(services):
    rs = services["resource_service"]
    resource = rs.create_resource("Currency Default Resource", role="Engineer")
    assert resource.currency_code == "EUR"


def test_cost_item_defaults_currency_to_eur(services):
    ps = services["project_service"]
    cs = services["cost_service"]

    project = ps.create_project("Currency Default Cost Project", "")
    item = cs.add_cost_item(
        project_id=project.id,
        description="Default currency item",
        planned_amount=100.0,
        cost_type=CostType.OVERHEAD,
    )
    assert item.currency_code == "EUR"


def test_project_resource_defaults_currency_to_eur(services):
    ps = services["project_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]

    project = ps.create_project("Currency Default PR Project", "")
    resource = rs.create_resource("Currency Default PR Resource")

    pr = prs.add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        hourly_rate=80.0,
        planned_hours=20.0,
    )
    assert pr.currency_code == "EUR"
