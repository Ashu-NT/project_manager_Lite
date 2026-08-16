"""Persistent performance evidence for the PM Dashboard and Portfolio workspaces."""

from __future__ import annotations

import time
import functools
from collections import Counter
from contextlib import contextmanager
from datetime import date, timedelta
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_dashboard_desktop_api,
    build_project_management_portfolio_desktop_api,
)
from src.tests.project_management._sql_measurement_helpers import (
    count_calls,
    measure_sql,
)
from src.ui_qml.modules.project_management.presenters.dashboard import (
    ProjectDashboardWorkspacePresenter,
)
from src.ui_qml.modules.project_management.presenters.portfolio import (
    ProjectPortfolioWorkspacePresenter,
)


@contextmanager
def _measure_call_time(targets: list[tuple[object, str, str]]):
    durations: Counter = Counter()
    saved: list[tuple[object, str, object]] = []
    for instance, method_name, label in targets:
        original = getattr(instance, method_name)
        saved.append((instance, method_name, original))

        def _wrapper(*args, _original=original, _label=label, **kwargs):
            started = time.perf_counter()
            try:
                return _original(*args, **kwargs)
            finally:
                durations[_label] += time.perf_counter() - started

        functools.update_wrapper(_wrapper, original)
        setattr(instance, method_name, _wrapper)
    try:
        yield durations
    finally:
        for instance, method_name, original in saved:
            setattr(instance, method_name, original)


def _seed_single_project_workspace(services):
    today = date.today()
    project = services["project_service"].create_project(
        "Workspace Performance Project",
        start_date=today,
        end_date=today + timedelta(days=30),
        financial_currency_code="EUR",
    )
    task = services["task_service"].create_task(
        project.id,
        "Workspace Performance Task",
        start_date=today,
        duration_days=10,
    )
    resource = services["resource_service"].create_resource(
        "Workspace Performance Resource",
        "Planner",
        hourly_rate=80.0,
        capacity_percent=100.0,
        currency_code="EUR",
        rate_effective_on=today,
    )
    project_resource = services["project_resource_service"].add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        planned_hours=40.0,
        hourly_rate=80.0,
        currency_code="EUR",
    )
    services["task_service"].assign_project_resource(
        task_id=task.id,
        project_resource_id=project_resource.id,
        allocation_percent=50.0,
    )

    portfolio_api = build_project_management_portfolio_desktop_api(
        project_service=services["project_service"],
        portfolio_service=services["portfolio_service"],
        pool_service=services["portfolio_resource_pool_service"],
    )
    template = portfolio_api.create_scoring_template(
        SimpleNamespace(
            name="Workspace Performance Template",
            summary="Measurement fixture",
            strategic_weight=1,
            value_weight=1,
            urgency_weight=1,
            risk_weight=1,
            activate=True,
        )
    )
    intake = portfolio_api.create_intake_item(
        SimpleNamespace(
            title="Workspace Performance Intake",
            sponsor_name="PMO",
            summary="Measurement fixture",
            requested_budget=20_000.0,
            requested_capacity_percent=20.0,
            target_start_date=today + timedelta(days=14),
            strategic_score=3,
            value_score=3,
            urgency_score=2,
            risk_score=1,
            scoring_template_id=template.id,
            status="APPROVED",
        )
    )
    portfolio_api.create_scenario(
        SimpleNamespace(
            name="Workspace Performance Scenario",
            budget_limit=200_000.0,
            capacity_limit_percent=200.0,
            project_ids=(project.id,),
            intake_item_ids=(intake.id,),
            notes="Measurement fixture",
        )
    )
    return project, portfolio_api


def test_measure_single_project_dashboard_and_portfolio_workspaces(
    services,
    capsys,
) -> None:
    project, portfolio_api = _seed_single_project_workspace(services)
    dashboard = services["dashboard_service"]
    reporting = services["reporting_service"]
    tasks = services["task_service"]
    resources = services["resource_service"]
    registers = services["register_service"]
    baselines = services["baseline_service"]
    collaboration = services["collaboration_service"]
    approvals = services["approval_service"]
    portfolio = services["portfolio_service"]
    pool = services["portfolio_resource_pool_service"]
    calendar_resolver = dashboard._sched._project_calendar_adapter._resolver

    dashboard_api = build_project_management_dashboard_desktop_api(
        project_service=services["project_service"],
        dashboard_service=dashboard,
        baseline_service=baselines,
        reporting_service=reporting,
        collaboration_service=collaboration,
        approval_service=approvals,
    )
    dashboard_presenter = ProjectDashboardWorkspacePresenter(desktop_api=dashboard_api)
    portfolio_presenter = ProjectPortfolioWorkspacePresenter(desktop_api=portfolio_api)

    dashboard_targets = [
        (dashboard, "get_dashboard_data", "dashboard.get_dashboard_data"),
        (dashboard._sched, "recalculate_project_schedule", "schedule.recalculate"),
        (reporting, "get_project_kpis", "reporting.get_project_kpis"),
        (reporting, "get_resource_load_summary", "reporting.get_resource_load_summary"),
        (reporting, "get_project_cost_source_breakdown", "reporting.get_cost_sources"),
        (reporting, "get_earned_value", "reporting.get_earned_value"),
        (reporting, "get_evm_series", "reporting.get_evm_series"),
        (tasks, "list_tasks_for_project", "tasks.list_for_project"),
        (tasks, "list_assignments_for_tasks", "tasks.list_assignments_for_tasks"),
        (tasks, "list_assignments_for_task", "tasks.list_assignments_for_task"),
        (resources, "list_resources", "resources.list_resources"),
        (registers, "get_dashboard_snapshot", "register.get_dashboard_snapshot"),
        (baselines, "list_baselines", "baseline.list_baselines"),
        (baselines, "get_approved_baseline", "baseline.get_approved"),
        (collaboration, "list_recent_activity", "collaboration.recent_activity"),
        (approvals, "list_pending", "approval.list_pending"),
        (calendar_resolver, "resolve_range", "calendar.resolve_range"),
        (
            calendar_resolver,
            "resolve_calendar_context",
            "calendar.resolve_single_day",
        ),
    ]
    with measure_sql(services["session"]) as dashboard_sql, count_calls(
        dashboard_targets
    ) as dashboard_calls, _measure_call_time(dashboard_targets) as dashboard_times:
        started = time.perf_counter()
        dashboard_state = dashboard_presenter.build_workspace_state(
            project_id=project.id,
            period_key="90d",
            view_key="executive",
        )
        dashboard_wall_time = time.perf_counter() - started

    portfolio_targets = [
        (portfolio, "list_scoring_templates", "portfolio.list_templates"),
        (portfolio, "list_intake_items", "portfolio.list_intake"),
        (portfolio, "list_scenarios", "portfolio.list_scenarios"),
        (portfolio, "list_portfolio_heatmap", "portfolio.list_heatmap"),
        (portfolio, "list_project_dependencies", "portfolio.list_dependencies"),
        (portfolio, "list_recent_pm_actions", "portfolio.list_recent_actions"),
        (portfolio, "evaluate_scenario", "portfolio.evaluate_scenario"),
        (pool, "get_pool_report", "portfolio.capacity_pool"),
        (portfolio._heatmap_reader, "read_facts", "portfolio_heatmap_reader.read_facts"),
        (portfolio._scenario_reader, "read_facts", "portfolio_scenario_reader.read_facts"),
        (pool._reader, "read_facts", "portfolio_pool_reader.read_facts"),
    ]
    with measure_sql(services["session"]) as portfolio_sql, count_calls(
        portfolio_targets
    ) as portfolio_calls, _measure_call_time(portfolio_targets) as portfolio_times:
        started = time.perf_counter()
        portfolio_state = portfolio_presenter.build_workspace_state()
        portfolio_wall_time = time.perf_counter() - started

    report = "\n".join(
        (
            "\n=== Dashboard/Portfolio single-project workspace baseline ===",
            f"dashboard_wall_time_s={dashboard_wall_time:.6f}",
            f"dashboard_db_time_s={dashboard_sql.total_db_time_s:.6f}",
            f"dashboard_sql_total={dashboard_sql.total_statements}",
            f"dashboard_sql_by_table={dict(dashboard_sql.by_table)}",
            f"dashboard_calls={dict(dashboard_calls)}",
            f"dashboard_stage_time_s={dict(dashboard_times)}",
            f"portfolio_wall_time_s={portfolio_wall_time:.6f}",
            f"portfolio_db_time_s={portfolio_sql.total_db_time_s:.6f}",
            f"portfolio_sql_total={portfolio_sql.total_statements}",
            f"portfolio_sql_by_table={dict(portfolio_sql.by_table)}",
            f"portfolio_calls={dict(portfolio_calls)}",
            f"portfolio_stage_time_s={dict(portfolio_times)}",
        )
    )
    print(report)
    with capsys.disabled():
        print(report)

    assert dashboard_state.selected_project_id == project.id
    assert portfolio_state.selected_scenario_id
    assert dashboard_calls["dashboard.get_dashboard_data"] == 1
    assert dashboard_calls["calendar.resolve_range"] <= 3
    assert dashboard_calls["calendar.resolve_single_day"] == 0
    assert portfolio_calls["portfolio.list_heatmap"] == 1
    assert dashboard_sql.total_statements > 0
    assert portfolio_sql.total_statements > 0


def test_dashboard_portfolio_scope_batches_shared_lookups_once_per_project(
    services,
) -> None:
    """R3.7: get_portfolio_data() must not re-fetch the full resource table or
    re-run CPM/per-task assignment lookups once per project on top of what
    get_project_kpis()/_build_upcoming_tasks() already need."""
    today = date.today()
    project_count = 4
    projects = []
    for index in range(project_count):
        project = services["project_service"].create_project(
            f"Portfolio Scale Project {index}",
            start_date=today,
            end_date=today + timedelta(days=30),
            financial_currency_code="EUR",
        )
        services["task_service"].create_task(
            project.id,
            f"Portfolio Scale Task {index}",
            start_date=today,
            duration_days=5,
        )
        projects.append(project)

    dashboard = services["dashboard_service"]
    resources = services["resource_service"]
    tasks = services["task_service"]
    scheduling_targets = [
        (dashboard._sched, "recalculate_project_schedule", "sched.recalculate"),
        (resources, "list_resources", "resources.list_resources"),
        (tasks, "list_tasks_for_project", "tasks.list_for_project"),
        (tasks, "list_assignments_for_tasks", "tasks.list_assignments_for_tasks"),
        (tasks, "list_assignments_for_task", "tasks.list_assignments_for_task"),
    ]

    with count_calls(scheduling_targets) as calls:
        data = dashboard.get_portfolio_data()

    assert data.portfolio.projects_total == project_count
    # Resources are fetched once for the whole portfolio, not once per project.
    assert calls["resources.list_resources"] == 1
    # CPM runs once per project (computed by get_portfolio_data and reused by
    # get_project_kpis via its schedule= override), not twice per project.
    assert calls["sched.recalculate"] == project_count
    # Assignments are fetched in one bulk call per project; the per-task
    # fallback (list_assignments_for_task) must never fire.
    assert calls["tasks.list_assignments_for_tasks"] == project_count
    assert calls["tasks.list_assignments_for_task"] == 0
