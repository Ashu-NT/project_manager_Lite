from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.domain.enums import CostType, DependencyType
from src.core.modules.project_management.domain.portfolio import PortfolioExecutiveRow
from src.core.modules.project_management.infrastructure.persistence.reads.portfolio import (
    SqlAlchemyPortfolioHeatmapReader,
)
from src.tests.project_management._test_repository_tenant_hardening_helpers import (
    _seed_priority_pm_rows,
)


def _legacy_heatmap_rows(services) -> list[PortfolioExecutiveRow]:
    portfolio = services["portfolio_service"]
    reporting = services["reporting_service"]
    rows: list[PortfolioExecutiveRow] = []
    for project in portfolio._accessible_projects():
        kpi = reporting.get_project_kpis(project.id)
        loads = reporting.get_resource_load_summary(project.id)
        peak = max((float(row.utilization_percent or 0.0) for row in loads), default=0.0)
        pressure = 2 if int(kpi.late_tasks or 0) > 0 else 0
        pressure += 1 if int(kpi.critical_tasks or 0) > 0 else 0
        pressure += 2 if peak >= 120.0 else 1 if peak >= 100.0 else 0
        pressure += 1 if float(kpi.cost_variance or 0.0) > 0 else 0
        rows.append(
            PortfolioExecutiveRow(
                project_id=project.id,
                project_name=project.name,
                project_status=getattr(project.status, "value", str(project.status)),
                critical_tasks=int(kpi.critical_tasks or 0),
                late_tasks=int(kpi.late_tasks or 0),
                peak_utilization_percent=round(peak, 1),
                cost_variance=float(kpi.cost_variance or 0.0),
                pressure_score=pressure,
                pressure_label=portfolio._pressure_label(pressure),
            )
        )
    return sorted(rows, key=lambda row: (-row.pressure_score, -row.late_tasks, row.project_name.lower()))


def test_heatmap_reader_preserves_schedule_load_cost_and_pressure(services) -> None:
    projects = services["project_service"]
    tasks = services["task_service"]
    resources = services["resource_service"]
    project_resources = services["project_resource_service"]

    pressured = projects.create_project(
        "Pressured",
        start_date=date(2024, 1, 8),
        end_date=date(2024, 3, 29),
        planned_budget=500.0,
        currency="EUR",
    )
    stable = projects.create_project("Stable", planned_budget=500.0, currency="EUR")
    first = tasks.create_task(
        pressured.id,
        "Build",
        start_date=date(2024, 1, 8),
        duration_days=5,
        deadline=date(2024, 1, 9),
    )
    second = tasks.create_task(
        pressured.id,
        "Release",
        start_date=date(2024, 1, 8),
        duration_days=5,
        deadline=date(2024, 1, 31),
    )
    tasks.add_dependency(first.id, second.id, DependencyType.FINISH_TO_START, lag_days=1)
    resource = resources.create_resource(
        "Lead",
        capacity_percent=80.0,
        hourly_rate=80.0,
        currency_code="EUR",
        rate_effective_on=date(2024, 1, 8),
    )
    project_resource = project_resources.add_to_project(
        project_id=pressured.id,
        resource_id=resource.id,
        planned_hours=1.0,
        hourly_rate=80.0,
        currency_code="EUR",
    )
    assignment = tasks.assign_project_resource(
        task_id=first.id,
        project_resource_id=project_resource.id,
        allocation_percent=100.0,
    )
    tasks.add_time_entry(
        assignment.id,
        entry_date=date(2024, 1, 8),
        hours=20.0,
        note="Executed work",
    )
    services["cost_service"].add_cost_item(
        pressured.id,
        "External delivery",
        planned_amount=50.0,
        committed_amount=100.0,
        actual_amount=500.0,
        incurred_date=date(2024, 1, 8),
        cost_type=CostType.MATERIAL,
        currency_code="EUR",
    )

    expected = _legacy_heatmap_rows(services)
    actual = services["portfolio_service"].list_portfolio_heatmap()

    assert isinstance(
        services["portfolio_service"]._heatmap_reader,
        SqlAlchemyPortfolioHeatmapReader,
    )
    assert actual == expected
    assert actual[0].project_id == pressured.id
    assert actual[0].pressure_label == "Hot"
    assert actual[0].peak_utilization_percent == 125.0
    assert actual[-1].project_id == stable.id


def test_concrete_heatmap_reader_rejects_cross_organization_ids(services) -> None:
    seeded = _seed_priority_pm_rows(services)
    portfolio = services["portfolio_service"]
    scope = portfolio._tenant_context_service.require_active_scope_ids(
        operation_label="test heatmap isolation"
    )

    facts = portfolio._heatmap_reader.read_facts(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_ids=(seeded["project_a"], seeded["project_b"]),
        as_of=date.today(),
    )

    assert {project.project_id for project in facts.projects} == {seeded["project_a"]}
    assert {resource.id for resource in facts.resources} == {seeded["resource_a"]}
    assert seeded["task_b1"] not in {
        task.id for project in facts.projects for task in project.tasks
    }


def test_heatmap_keeps_a_stable_row_when_one_project_fact_is_invalid(services, monkeypatch) -> None:
    project = services["project_service"].create_project("Invalid facts", currency="EUR")
    task = services["task_service"].create_task(
        project.id,
        "Invalid status source",
        start_date=date(2024, 1, 8),
        duration_days=2,
    )
    portfolio = services["portfolio_service"]
    scope = portfolio._tenant_context_service.require_active_scope_ids(
        operation_label="test heatmap fallback"
    )
    facts = portfolio._heatmap_reader.read_facts(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_ids=(project.id,),
        as_of=date.today(),
    )
    bad_task = replace(facts.projects[0].tasks[0], status="NOT_A_TASK_STATUS")
    bad_project = replace(facts.projects[0], tasks=(bad_task,))
    monkeypatch.setattr(
        portfolio._heatmap_reader,
        "read_facts",
        lambda **_kwargs: replace(facts, projects=(bad_project,)),
    )

    rows = portfolio.list_portfolio_heatmap()

    assert len(rows) == 1
    assert rows[0].project_id == project.id
    assert rows[0].pressure_score == 0
    assert rows[0].pressure_label == "Stable"
