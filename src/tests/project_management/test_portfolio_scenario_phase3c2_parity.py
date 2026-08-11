from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.core.modules.project_management.infrastructure.persistence.reads.portfolio import (
    SqlAlchemyPortfolioScenarioReader,
)
from src.tests.project_management._test_repository_tenant_hardening_helpers import (
    _seed_priority_pm_rows,
)


def _assign(
    services,
    *,
    project_id: str,
    task_id: str,
    resource_id: str,
    allocation: float,
) -> None:
    project_resource = services["project_resource_service"].add_to_project(
        project_id=project_id,
        resource_id=resource_id,
        planned_hours=40.0,
        hourly_rate=80.0,
        currency_code="EUR",
    )


def _approve_budget(services, project_id: str, amount: str) -> None:
    configuration = services["financial_configuration_service"]
    budgets = services["budget_service"]
    code = configuration.create_cost_code(
        code=f"SCN-{project_id[:8]}",
        name="Scenario budget",
    )
    budget = budgets.create_budget(project_id, "Approved scenario budget")
    budgets.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Authorized amount",
        amount=Decimal(amount),
        expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(
        budget.id,
        "admin",
        expected_version=budget.row_version,
    )
    budgets.approve_budget(
        budget.id,
        approved_by="admin",
        expected_version=budget.row_version,
    )
    services["task_service"].assign_project_resource(
        task_id=task_id,
        project_resource_id=project_resource.id,
        allocation_percent=allocation,
    )


def test_scenario_reader_preserves_capacity_budget_intake_and_comparison(services) -> None:
    projects = services["project_service"]
    tasks = services["task_service"]
    resources = services["resource_service"]
    portfolio = services["portfolio_service"]

    shared = resources.create_resource(
        "Shared",
        capacity_percent=100.0,
        hourly_rate=80.0,
        currency_code="EUR",
        rate_effective_on=date(2024, 1, 8),
    )
    specialist = resources.create_resource(
        "Specialist",
        capacity_percent=50.0,
        hourly_rate=80.0,
        currency_code="EUR",
        rate_effective_on=date(2024, 1, 8),
    )
    resources.create_resource(
        "Inactive capacity",
        is_active=False,
        capacity_percent=900.0,
        currency_code="EUR",
    )
    alpha = projects.create_project("Alpha", financial_currency_code="EUR")
    beta = projects.create_project("Beta", financial_currency_code="EUR")
    _approve_budget(services, alpha.id, "400")
    _approve_budget(services, beta.id, "700")

    alpha_scheduled = tasks.create_task(
        alpha.id,
        "Alpha scheduled",
        start_date=date(2024, 1, 8),
        duration_days=5,
    )
    alpha_unscheduled = tasks.create_task(alpha.id, "Alpha unscheduled")
    _assign(
        services,
        project_id=alpha.id,
        task_id=alpha_scheduled.id,
        resource_id=shared.id,
        allocation=60.0,
    )
    services["task_service"].assign_resource(alpha_unscheduled.id, shared.id, 20.0)

    beta_task = tasks.create_task(
        beta.id,
        "Beta scheduled",
        start_date=date(2024, 1, 8),
        duration_days=5,
    )
    _assign(
        services,
        project_id=beta.id,
        task_id=beta_task.id,
        resource_id=shared.id,
        allocation=70.0,
    )
    _assign(
        services,
        project_id=beta.id,
        task_id=beta_task.id,
        resource_id=specialist.id,
        allocation=50.0,
    )

    intake = portfolio.create_intake_item(
        title="Intake",
        sponsor_name="PMO",
        requested_budget=200.0,
        requested_capacity_percent=30.0,
        strategic_score=5,
        value_score=4,
        urgency_score=3,
        risk_score=2,
    )
    base = portfolio.create_scenario(
        name="Base",
        budget_limit=500.0,
        capacity_limit_percent=None,
        project_ids=[alpha.id],
        intake_item_ids=[intake.id],
    )
    candidate = portfolio.create_scenario(
        name="Candidate",
        budget_limit=2_000.0,
        capacity_limit_percent=250.0,
        project_ids=[alpha.id, beta.id],
        intake_item_ids=[],
    )

    base_result = portfolio.evaluate_scenario(base.id)
    comparison = portfolio.compare_scenarios(base.id, candidate.id)

    assert isinstance(portfolio._scenario_reader, SqlAlchemyPortfolioScenarioReader)
    assert base_result.total_budget == pytest.approx(600.0)
    assert base_result.total_capacity_percent == pytest.approx(110.0)
    assert base_result.available_capacity_percent == pytest.approx(150.0)
    assert base_result.capacity_limit_percent == pytest.approx(150.0)
    assert base_result.intake_composite_score == intake.composite_score
    assert base_result.over_budget is True
    assert base_result.over_capacity is False

    assert comparison.base_evaluation == base_result
    assert comparison.candidate_evaluation.total_budget == pytest.approx(1_100.0)
    assert comparison.candidate_evaluation.total_capacity_percent == pytest.approx(200.0)
    assert comparison.budget_delta == pytest.approx(500.0)
    assert comparison.capacity_delta_percent == pytest.approx(90.0)
    assert comparison.added_project_names == ["Beta"]
    assert comparison.removed_intake_titles == ["Intake"]


def test_scenario_comparison_reads_one_fact_graph(services, monkeypatch) -> None:
    portfolio = services["portfolio_service"]
    project = services["project_service"].create_project(
        "Single", financial_currency_code="EUR"
    )
    base = portfolio.create_scenario(name="Base", project_ids=[project.id], intake_item_ids=[])
    candidate = portfolio.create_scenario(
        name="Candidate",
        project_ids=[project.id],
        intake_item_ids=[],
    )
    calls = 0
    original = portfolio._scenario_reader.read_facts

    def _read_once(**kwargs):
        nonlocal calls
        calls += 1
        return original(**kwargs)

    monkeypatch.setattr(portfolio._scenario_reader, "read_facts", _read_once)

    portfolio.compare_scenarios(base.id, candidate.id)

    assert calls == 1


def test_concrete_scenario_reader_rejects_cross_organization_ids(services) -> None:
    seeded = _seed_priority_pm_rows(services)
    portfolio = services["portfolio_service"]
    scope = portfolio._tenant_context_service.require_active_scope_ids(
        operation_label="test scenario isolation"
    )

    facts = portfolio._scenario_reader.read_facts(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        scenario_ids=(),
        accessible_project_ids=(seeded["project_a"], seeded["project_b"]),
    )

    assert {project.id for project in facts.projects} == {seeded["project_a"]}
    assert {resource.id for resource in facts.resources} == {seeded["resource_a"]}
    assert seeded["task_b1"] not in {task.id for task in facts.tasks}
