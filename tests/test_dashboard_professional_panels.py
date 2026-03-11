from __future__ import annotations

from datetime import date

from core.domain.enums import TaskStatus
from core.models import DependencyType
from tests.ui_runtime_helpers import make_settings_store
from ui.dashboard.layout_builder import DashboardLayoutDialog
from ui.dashboard.tab import DashboardTab


def _seed_professional_project(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project(
        "Professional Dashboard Project",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 5, 15),
    )
    planner = rs.create_resource("Lead Planner", role="PM", hourly_rate=120.0)
    engineer = rs.create_resource("Execution Lead", role="Engineer", hourly_rate=100.0)

    kickoff = ts.create_task(
        project.id,
        "Kickoff Milestone",
        start_date=date(2026, 4, 1),
        duration_days=0,
        status=TaskStatus.DONE,
        priority=80,
    )
    design = ts.create_task(
        project.id,
        "Critical Design",
        start_date=date(2026, 4, 2),
        duration_days=3,
        status=TaskStatus.IN_PROGRESS,
        priority=95,
    )
    gate = ts.create_task(
        project.id,
        "Deployment Gate",
        duration_days=1,
        deadline=date(2026, 4, 10),
        status=TaskStatus.TODO,
        priority=100,
    )

    ts.assign_resource(kickoff.id, planner.id, allocation_percent=40.0)
    ts.assign_resource(design.id, planner.id, allocation_percent=60.0)
    ts.assign_resource(gate.id, engineer.id, allocation_percent=80.0)
    ts.add_dependency(design.id, gate.id, DependencyType.FINISH_TO_START, lag_days=0)
    return {
        "project": project,
        "kickoff": kickoff,
        "design": design,
        "gate": gate,
    }


def test_dashboard_service_builds_milestone_and_watchlist_rows(services):
    seeded = _seed_professional_project(services)

    data = services["dashboard_service"].get_dashboard_data(seeded["project"].id)

    milestone_names = {row.task_name for row in data.milestone_health}
    watchlist_names = {row.task_name for row in data.critical_watchlist}
    assert "Kickoff Milestone" in milestone_names
    assert "Deployment Gate" in milestone_names
    assert "Critical Design" in watchlist_names or "Deployment Gate" in watchlist_names
    assert any((row.owner_name or "") == "Lead Planner" for row in data.milestone_health)
    assert any(row.total_float_days == 0 for row in data.critical_watchlist)


def test_dashboard_layout_dialog_exposes_professional_project_panels(qapp):
    dialog = DashboardLayoutDialog(None, current_layout={}, portfolio_mode=False)

    assert "milestones" in dialog._panel_checks
    assert "watchlist" in dialog._panel_checks
    assert dialog._panel_checks["milestones"].isChecked() is True
    assert dialog._panel_checks["watchlist"].isChecked() is True


def test_dashboard_tab_can_surface_professional_panels_at_runtime(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    seeded = _seed_professional_project(services)
    store = make_settings_store(repo_workspace, prefix="dashboard-professional")
    store.save_dashboard_layout(
        {
            "project": {
                "visible_panels": ["milestones", "watchlist", "kpi"],
                "panel_order": ["milestones", "watchlist", "kpi", "resource", "evm", "burndown"],
            },
            "portfolio": {
                "visible_panels": ["portfolio", "resource", "burndown"],
                "panel_order": ["portfolio", "resource", "burndown", "kpi"],
            },
        }
    )

    def _sync_refresh(tab, *, show_progress=False):
        project_id, project_name = tab._current_project_id_and_name()
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
        tab._update_professional_panels(data)
        tab._sync_leveling_buttons()

    monkeypatch.setattr("ui.dashboard.data_ops.run_refresh_dashboard_async", _sync_refresh)

    tab = DashboardTab(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        settings_store=store,
        user_session=services["user_session"],
    )

    assert tab.project_combo.currentData() == seeded["project"].id
    assert tab._current_visible_panel_ids() == ["milestones", "watchlist", "kpi"]
    assert tab._active_dashboard_panel_count() == 3
    assert tab.milestone_group.isHidden() is False
    assert tab.watchlist_group.isHidden() is False
    assert tab.kpi_group.isHidden() is False
    assert tab.milestone_table.rowCount() >= 2
    assert tab.watchlist_table.rowCount() >= 1
