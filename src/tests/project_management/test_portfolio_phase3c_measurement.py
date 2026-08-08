"""Phase 3C measurements for Portfolio read candidates and completed cutovers."""

from __future__ import annotations

import time
from datetime import date

import pytest

from src.tests.project_management.test_reporting_financials_phase3b_measurement import (
    count_calls,
    measure_sql,
)


_SIZES = {
    "small": 1,
    "medium": 5,
    "large": 12,
}


def _seed_portfolio(services, *, project_count: int) -> tuple[str, str]:
    project_service = services["project_service"]
    task_service = services["task_service"]
    resource_service = services["resource_service"]
    project_resource_service = services["project_resource_service"]
    portfolio = services["portfolio_service"]

    project_ids: list[str] = []
    for index in range(project_count):
        project = project_service.create_project(
            f"Phase 3C Project {index}",
            start_date=date(2024, 1, 8),
            end_date=date(2024, 3, 29),
            planned_budget=10_000.0 + index,
            currency="EUR",
        )
        task = task_service.create_task(
            project.id,
            f"Phase 3C Task {index}",
            start_date=date(2024, 1, 8),
            duration_days=10,
        )
        resource = resource_service.create_resource(
            f"Phase 3C Resource {index}",
            "Developer",
            hourly_rate=75.0,
            capacity_percent=100.0,
            currency_code="EUR",
            rate_effective_on=date(2024, 1, 8),
        )
        project_resource = project_resource_service.add_to_project(
            project_id=project.id,
            resource_id=resource.id,
            planned_hours=40.0,
            hourly_rate=75.0,
            currency_code="EUR",
        )
        task_service.assign_project_resource(
            task_id=task.id,
            project_resource_id=project_resource.id,
            allocation_percent=50.0,
        )
        project_ids.append(project.id)

    split = max(1, (project_count + 1) // 2)
    base = portfolio.create_scenario(
        name="Phase 3C Base",
        budget_limit=1_000_000.0,
        capacity_limit_percent=10_000.0,
        project_ids=project_ids[:split],
        intake_item_ids=[],
    )
    candidate = portfolio.create_scenario(
        name="Phase 3C Candidate",
        budget_limit=1_000_000.0,
        capacity_limit_percent=10_000.0,
        project_ids=project_ids,
        intake_item_ids=[],
    )
    return base.id, candidate.id


@pytest.mark.parametrize("size_name", ["small", "medium", "large"])
def test_phase3c_measure_portfolio_read_candidates(services, size_name, capsys) -> None:
    project_count = _SIZES[size_name]
    base_id, candidate_id = _seed_portfolio(services, project_count=project_count)
    portfolio = services["portfolio_service"]
    reporting = services["reporting_service"]
    pool = services["portfolio_resource_pool_service"]

    targets = [
        (portfolio, "_accessible_projects", "portfolio._accessible_projects"),
        (reporting, "get_project_kpis", "reporting.get_project_kpis"),
        (
            reporting,
            "get_resource_load_summary",
            "reporting.get_resource_load_summary",
        ),
        (portfolio._project_repo, "list", "project_repo.list"),
        (portfolio._project_repo, "get", "project_repo.get"),
        (portfolio._scenario_repo, "get", "scenario_repo.get"),
        (portfolio._intake_repo, "list", "intake_repo.list"),
        (reporting._task_repo, "list_by_project", "task_repo.list_by_project"),
        (reporting._task_repo, "get", "task_repo.get"),
        (reporting._assignment_repo, "list_by_tasks", "assignment_repo.list_by_tasks"),
        (
            reporting._assignment_repo,
            "list_by_resource",
            "assignment_repo.list_by_resource",
        ),
        (reporting._resource_repo, "list", "resource_repo.list"),
        (reporting._resource_repo, "get", "resource_repo.get"),
        (pool._reader, "read_facts", "portfolio_pool_reader.read_facts"),
        (portfolio._scenario_reader, "read_facts", "portfolio_scenario_reader.read_facts"),
        (portfolio._heatmap_reader, "read_facts", "portfolio_heatmap_reader.read_facts"),
        (
            portfolio._project_calendar_adapter,
            "working_day_dates_between",
            "project_calendar.working_day_dates_between",
        ),
        (portfolio._rate_resolver, "resolve_many", "rate_resolver.resolve_many"),
        (
            pool._calendar,
            "working_day_dates_between",
            "calendar.working_day_dates_between",
        ),
    ]
    operations = (
        ("heatmap", portfolio.list_portfolio_heatmap),
        (
            "scenario_comparison",
            lambda: portfolio.compare_scenarios(base_id, candidate_id),
        ),
        (
            "capacity_pool",
            lambda: pool.get_pool_report(date(2024, 1, 1), date(2024, 3, 31)),
        ),
    )

    for operation_name, operation in operations:
        identity_before = len(services["session"].identity_map)
        with measure_sql(services["session"]) as sql_stats, count_calls(targets) as calls:
            started = time.perf_counter()
            result = operation()
            wall_time = time.perf_counter() - started
        identity_delta = len(services["session"].identity_map) - identity_before
        report = "\n".join(
            (
                f"\n=== Phase 3C measurement [{size_name}:{operation_name}] ===",
                f"projects={project_count}",
                f"wall_time_s={wall_time:.6f}",
                f"db_time_s={sql_stats.total_db_time_s:.6f}",
                f"sql_total_statements={sql_stats.total_statements}",
                f"sql_by_table={dict(sql_stats.by_table)}",
                f"identity_map_delta={identity_delta}",
                f"call_counts={dict(calls)}",
            )
        )
        print(report)
        with capsys.disabled():
            print(report)

        assert result is not None
        assert sql_stats.total_statements > 0
        if operation_name == "capacity_pool":
            assert sql_stats.total_statements == 5
            assert calls["portfolio_pool_reader.read_facts"] == 1
            assert calls["calendar.working_day_dates_between"] == 1
            assert calls["resource_repo.list"] == 0
            assert calls["resource_repo.get"] == 0
            assert calls["assignment_repo.list_by_resource"] == 0
            assert calls["task_repo.get"] == 0
            assert calls["project_repo.get"] == 0
        elif operation_name == "scenario_comparison":
            assert sql_stats.total_statements == 12
            assert calls["portfolio_scenario_reader.read_facts"] == 1
            assert calls["calendar.working_day_dates_between"] == 1
            assert calls["portfolio._accessible_projects"] == 1
            assert calls["project_repo.list"] == 1
            assert calls["scenario_repo.get"] == 0
            assert calls["intake_repo.list"] == 0
            assert calls["reporting.get_resource_load_summary"] == 0
            assert calls["task_repo.list_by_project"] == 0
            assert calls["assignment_repo.list_by_tasks"] == 0
            assert calls["resource_repo.list"] == 0
            assert calls["resource_repo.get"] == 0
        elif operation_name == "heatmap":
            expected_sql = {1: 17, 5: 41, 12: 83}[project_count]
            assert sql_stats.total_statements == expected_sql
            assert calls["portfolio_heatmap_reader.read_facts"] == 1
            assert calls["project_calendar.working_day_dates_between"] == project_count
            assert calls["rate_resolver.resolve_many"] == project_count
            assert calls["portfolio._accessible_projects"] == 1
            assert calls["project_repo.list"] == 1
            assert calls["reporting.get_project_kpis"] == 0
            assert calls["reporting.get_resource_load_summary"] == 0
            assert calls["project_repo.get"] == 0
            assert calls["task_repo.list_by_project"] == 0
            assert calls["assignment_repo.list_by_tasks"] == 0
            assert calls["resource_repo.list"] == 0
            assert calls["resource_repo.get"] == 0
