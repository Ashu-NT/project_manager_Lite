from __future__ import annotations

from datetime import date

import pytest

from src.tests.project_management._test_repository_tenant_hardening_helpers import (
    _seed_priority_pm_rows,
)

def test_capacity_reader_preserves_cross_project_demand_and_utilization(services) -> None:
    project_service = services["project_service"]
    task_service = services["task_service"]
    resource_service = services["resource_service"]
    project_resource_service = services["project_resource_service"]
    pool_service = services["portfolio_resource_pool_service"]

    resource = resource_service.create_resource(
        "Shared Capacity",
        "Engineer",
        capacity_percent=100.0,
        hourly_rate=80.0,
        currency_code="EUR",
        rate_effective_on=date(2024, 1, 8),
    )
    allocations = (("Alpha", 60.0), ("Beta", 70.0))
    project_ids: list[str] = []
    for project_name, allocation in allocations:
        project = project_service.create_project(
            project_name,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 1, 12),
            financial_currency_code="EUR",
        )
        task = task_service.create_task(
            project.id,
            f"{project_name} delivery",
            start_date=date(2024, 1, 8),
            duration_days=5,
        )
        project_resource = project_resource_service.add_to_project(
            project_id=project.id,
            resource_id=resource.id,
            planned_hours=40.0,
            hourly_rate=80.0,
            currency_code="EUR",
        )
        task_service.assign_project_resource(
            task_id=task.id,
            project_resource_id=project_resource.id,
            allocation_percent=allocation,
        )
        project_ids.append(project.id)

    report = pool_service.get_pool_report(
        date(2024, 1, 8),
        date(2024, 1, 12),
        resource_ids=[resource.id, "outside-scope"],
    )

    assert len(report.pool) == 1
    summary = report.pool[0]
    assert summary.resource_id == resource.id
    assert summary.resource_name == "Shared Capacity"
    assert summary.capacity_percent == pytest.approx(100.0)
    assert summary.peak_load_percent == pytest.approx(130.0)
    assert summary.average_load_percent == pytest.approx(130.0)
    assert summary.overloaded is True
    assert {row.project_id for row in summary.demands} == set(project_ids)
    assert {row.project_name for row in summary.demands} == {"Alpha", "Beta"}
    assert {row.total_allocation_percent for row in summary.demands} == {60.0, 70.0}

    direct_demands = pool_service.get_resource_demand_by_project(
        resource.id,
        date(2024, 1, 8),
        date(2024, 1, 12),
    )
    assert direct_demands == summary.demands


def test_capacity_reader_returns_empty_result_for_out_of_scope_resource_id(services) -> None:
    report = services["portfolio_resource_pool_service"].get_pool_report(
        date(2024, 1, 8),
        date(2024, 1, 12),
        resource_ids=["outside-scope"],
    )

    assert report.pool == []


def test_concrete_capacity_reader_excludes_other_organization_resources(services) -> None:
    seeded = _seed_priority_pm_rows(services)

    report = services["portfolio_resource_pool_service"].get_pool_report(
        date(2024, 1, 8),
        date(2024, 1, 12),
    )

    assert {row.resource_id for row in report.pool} == {seeded["resource_a"]}
    assert seeded["resource_b"] not in {row.resource_id for row in report.pool}
