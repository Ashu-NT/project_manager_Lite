from __future__ import annotations

from datetime import date, timedelta

from core.modules.project_management.domain.enums import ProjectStatus, TaskStatus
from core.modules.project_management.services.dashboard import PORTFOLIO_SCOPE_ID
from tests.ui_runtime_helpers import make_settings_store
from ui.modules.project_management.dashboard.tab import DashboardTab


def _seed_portfolio_dashboard(services):
    today = date.today()
    project_service = services["project_service"]
    task_service = services["task_service"]
    resource_service = services["resource_service"]
    project_resource_service = services["project_resource_service"]
    timesheet_service = services["timesheet_service"]
    cost_service = services["cost_service"]

    alpha = project_service.create_project(
        "Alpha Program",
        start_date=today,
        end_date=today + timedelta(days=30),
        planned_budget=1200.0,
    )
    beta = project_service.create_project(
        "Beta Recovery",
        start_date=today + timedelta(days=1),
        end_date=today + timedelta(days=20),
        planned_budget=800.0,
    )
    project_service.set_status(alpha.id, ProjectStatus.ACTIVE)
    project_service.set_status(beta.id, ProjectStatus.ON_HOLD)

    shared = resource_service.create_resource("Shared Engineer", hourly_rate=100.0, capacity_percent=100.0)
    analyst = resource_service.create_resource("Portfolio Analyst", hourly_rate=80.0, capacity_percent=100.0)

    alpha_shared = project_resource_service.add_to_project(alpha.id, shared.id, hourly_rate=100.0)
    alpha_analyst = project_resource_service.add_to_project(alpha.id, analyst.id, hourly_rate=80.0)
    beta_shared = project_resource_service.add_to_project(beta.id, shared.id, hourly_rate=100.0)

    alpha_build = task_service.create_task(
        alpha.id,
        "Alpha Build",
        start_date=today + timedelta(days=2),
        duration_days=3,
        status=TaskStatus.IN_PROGRESS,
        priority=90,
    )
    alpha_close = task_service.create_task(
        alpha.id,
        "Alpha Closeout",
        start_date=today + timedelta(days=5),
        duration_days=2,
        status=TaskStatus.DONE,
        priority=50,
    )
    beta_replan = task_service.create_task(
        beta.id,
        "Beta Replan",
        start_date=today + timedelta(days=3),
        duration_days=4,
        status=TaskStatus.TODO,
        priority=75,
    )
    task_service.set_status(alpha_build.id, TaskStatus.IN_PROGRESS)
    task_service.set_status(alpha_close.id, TaskStatus.DONE)

    alpha_shared_assignment = task_service.assign_project_resource(alpha_build.id, alpha_shared.id, 60.0)
    task_service.assign_project_resource(alpha_close.id, alpha_analyst.id, 30.0)
    beta_shared_assignment = task_service.assign_project_resource(beta_replan.id, beta_shared.id, 80.0)

    timesheet_service.add_time_entry(
        alpha_shared_assignment.id,
        entry_date=today + timedelta(days=2),
        hours=6.0,
        note="Alpha execution",
    )
    timesheet_service.add_time_entry(
        beta_shared_assignment.id,
        entry_date=today + timedelta(days=3),
        hours=4.0,
        note="Beta recovery planning",
    )

    cost_service.add_cost_item(
        alpha.id,
        "Alpha vendor overrun",
        planned_amount=120.0,
        actual_amount=220.0,
    )
    cost_service.add_cost_item(
        beta.id,
        "Beta retained support",
        planned_amount=80.0,
        actual_amount=40.0,
    )
    return {
        "alpha": alpha,
        "beta": beta,
    }


def test_dashboard_service_builds_portfolio_data_across_projects(services):
    _seed_portfolio_dashboard(services)

    data = services["dashboard_service"].get_portfolio_data()

    assert data.kpi.project_id == PORTFOLIO_SCOPE_ID
    assert data.portfolio is not None
    assert data.portfolio.projects_total == 2
    assert data.portfolio.active_projects == 1
    assert data.portfolio.on_hold_projects == 1
    assert data.kpi.tasks_total == 3
    assert data.kpi.tasks_completed == 1
    assert any(row.status_label == "ACTIVE" and row.project_count == 1 for row in data.portfolio.status_rollup)
    assert any(row.status_label == "ON_HOLD" and row.project_count == 1 for row in data.portfolio.status_rollup)
    assert any(row.project_name == "Beta Recovery" and row.project_status == "ON_HOLD" for row in data.portfolio.project_rankings)
    assert any(
        row.resource_name == "Shared Engineer"
        and float(row.total_allocation_percent or 0.0) >= 140.0
        and float(row.utilization_percent or 0.0) >= 140.0
        for row in data.resource_load
    )
    assert any("at risk across the portfolio" in msg.lower() for msg in data.alerts)


def test_dashboard_tab_switches_into_portfolio_mode_at_runtime(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    seeded = _seed_portfolio_dashboard(services)

    def _sync_refresh(tab, *, show_progress=False):
        project_id, project_name = tab._current_project_id_and_name()
        if project_id == PORTFOLIO_SCOPE_ID:
            data = services["dashboard_service"].get_portfolio_data()
            overloaded = [
                row
                for row in data.resource_load
                if float(getattr(row, "utilization_percent", row.total_allocation_percent) or 0.0) > 100.0
            ]
            tab._current_conflicts = []
            tab._current_data = data
            tab._update_summary(project_name, data)
            tab._update_kpis(data)
            tab._update_burndown_chart(data)
            tab._update_resource_chart(data)
            tab._update_alerts(data)
            tab._update_conflicts_from_load(overloaded)
            tab._update_upcoming(data)
            tab._update_evm(data)
            tab._update_portfolio_panel(data)
            tab._sync_leveling_buttons()
            return

        data = services["dashboard_service"].get_dashboard_data(project_id)
        tab._current_conflicts = []
        tab._current_data = data
        tab._update_summary(project_name, data)
        tab._update_kpis(data)
        tab._update_burndown_chart(data)
        tab._update_resource_chart(data)
        tab._update_alerts(data)
        tab._update_conflicts_from_load([])
        tab._update_upcoming(data)
        tab._update_evm(data)
        tab._update_portfolio_panel(data)
        tab._sync_leveling_buttons()

    monkeypatch.setattr("ui.modules.project_management.dashboard.data_ops.run_refresh_dashboard_async", _sync_refresh)

    tab = DashboardTab(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        settings_store=make_settings_store(repo_workspace, prefix="portfolio-dashboard"),
        user_session=services["user_session"],
    )

    assert tab.project_combo.currentData() == seeded["alpha"].id
    portfolio_index = tab.project_combo.findData(PORTFOLIO_SCOPE_ID)
    assert portfolio_index >= 0

    tab.project_combo.setCurrentIndex(portfolio_index)

    assert tab.project_title_lbl.text() == "Portfolio Overview"
    assert tab.baseline_combo.currentText() == "Portfolio view"
    assert tab.portfolio_group.isHidden() is False
    assert tab.evm_group.isHidden() is True
    assert tab.portfolio_table.rowCount() == 2
    assert tab.burndown_chart.ax.get_title() == "Portfolio status rollup"
    assert tab.resource_chart.ax.get_title() == "Cross-project resource capacity"
    assert tab._active_dashboard_panel_count() == 4
    assert tab.btn_auto_level.isEnabled() is False
    assert tab.btn_manual_shift.isEnabled() is False


def test_dashboard_tab_preserves_authenticated_session(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    services["project_service"].create_project(
        "Dashboard Session Project",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
    )
    monkeypatch.setattr("ui.modules.project_management.dashboard.data_ops.run_refresh_dashboard_async", lambda *_args, **_kwargs: None)

    tab = DashboardTab(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        settings_store=make_settings_store(repo_workspace, prefix="dashboard-session"),
        user_session=services["user_session"],
    )

    assert getattr(tab, "_user_session", None) is services["user_session"]
