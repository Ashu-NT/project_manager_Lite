from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from matplotlib.colors import to_rgba

from core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.risk.register import RegisterEntrySeverity, RegisterEntryType
from core.modules.project_management.domain.enums import DependencyType
from tests.ui_runtime_helpers import make_settings_store
from ui.modules.project_management.dashboard.layout_builder import DashboardLayoutDialog
from ui.modules.project_management.dashboard.tab import DashboardTab
from ui.modules.project_management.dashboard.widgets import ChartWidget
from src.ui.shared.formatting.theme_tokens import DARK_THEME, apply_theme_tokens
from src.ui.shared.formatting.ui_config import UIConfig as CFG


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


def test_dashboard_service_builds_register_summary_rows(services):
    seeded = _seed_professional_project(services)
    services["register_service"].create_entry(
        seeded["project"].id,
        entry_type=RegisterEntryType.RISK,
        title="Critical supplier dependency",
        severity=RegisterEntrySeverity.CRITICAL,
        owner_name="Lead Planner",
        due_date=date(2026, 4, 3),
    )
    services["register_service"].create_entry(
        seeded["project"].id,
        entry_type=RegisterEntryType.ISSUE,
        title="Blocked test environment",
        severity=RegisterEntrySeverity.HIGH,
        owner_name="Execution Lead",
    )

    data = services["dashboard_service"].get_dashboard_data(seeded["project"].id)

    assert data.register_summary is not None
    assert data.register_summary.open_risks == 1
    assert data.register_summary.open_issues == 1
    assert data.register_summary.critical_items == 1
    assert data.register_summary.urgent_items[0].title == "Critical supplier dependency"


def test_dashboard_layout_dialog_exposes_professional_project_panels(qapp):
    dialog = DashboardLayoutDialog(None, current_layout={}, portfolio_mode=False)

    assert "milestones" in dialog._panel_checks
    assert "watchlist" in dialog._panel_checks
    assert "register" in dialog._panel_checks
    assert dialog._panel_checks["milestones"].isChecked() is True
    assert dialog._panel_checks["watchlist"].isChecked() is True
    assert dialog._panel_checks["register"].isChecked() is True


def test_dashboard_chart_widget_respects_dark_theme_surface_colors(qapp):
    original_mode = "dark" if CFG.COLOR_BG_SURFACE == DARK_THEME["COLOR_BG_SURFACE"] else "light"
    apply_theme_tokens("dark")
    try:
        chart = ChartWidget("Dark Theme Chart")
        chart.ax.set_title("Burndown")
        chart.ax.set_xlabel("Date")
        chart.ax.set_ylabel("Remaining")
        chart.ax.text(0.5, 0.5, "12")
        chart.redraw()

        assert chart.fig.get_facecolor()[:3] == to_rgba(CFG.COLOR_BG_SURFACE)[:3]
        assert chart.ax.get_facecolor()[:3] == to_rgba(CFG.COLOR_BG_SURFACE_ALT)[:3]
        assert chart.ax.title.get_color() == CFG.COLOR_TEXT_PRIMARY
        assert chart.ax.xaxis.label.get_color() == CFG.COLOR_TEXT_SECONDARY
        assert chart.ax.yaxis.label.get_color() == CFG.COLOR_TEXT_SECONDARY
        assert chart.ax.texts[0].get_color() == CFG.COLOR_TEXT_PRIMARY
    finally:
        apply_theme_tokens(original_mode)


def test_dashboard_tab_panel_surface_uses_theme_background(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    original_mode = "dark" if CFG.COLOR_BG_SURFACE == DARK_THEME["COLOR_BG_SURFACE"] else "light"
    apply_theme_tokens("dark")
    monkeypatch.setattr("ui.modules.project_management.dashboard.data_ops.run_refresh_dashboard_async", lambda *_args, **_kwargs: None)
    try:
        services["project_service"].create_project("Dark Surface Dashboard")
        tab = DashboardTab(
            project_service=services["project_service"],
            dashboard_service=services["dashboard_service"],
            baseline_service=services["baseline_service"],
            settings_store=make_settings_store(repo_workspace, prefix="dashboard-surface"),
            user_session=services["user_session"],
        )

        assert tab.panel_scroll.objectName() == "dashboardPanelScroll"
        assert tab.panel_scroll.viewport().objectName() == "dashboardPanelViewport"
        assert tab.panel_canvas.objectName() == "dashboardPanelCanvas"
        assert tab.panel_canvas.testAttribute(Qt.WA_StyledBackground) is True
        assert CFG.COLOR_BG_APP in tab.styleSheet()
    finally:
        apply_theme_tokens(original_mode)


def test_dashboard_tab_can_surface_professional_panels_at_runtime(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    seeded = _seed_professional_project(services)
    services["register_service"].create_entry(
        seeded["project"].id,
        entry_type=RegisterEntryType.RISK,
        title="Runtime risk",
        severity=RegisterEntrySeverity.CRITICAL,
        owner_name="Lead Planner",
    )
    store = make_settings_store(repo_workspace, prefix="dashboard-professional")
    store.save_dashboard_layout(
        {
            "project": {
                "visible_panels": ["milestones", "watchlist", "register", "kpi"],
                "panel_order": ["milestones", "watchlist", "register", "kpi", "resource", "evm", "burndown"],
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

    monkeypatch.setattr("ui.modules.project_management.dashboard.data_ops.run_refresh_dashboard_async", _sync_refresh)

    tab = DashboardTab(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        settings_store=store,
        user_session=services["user_session"],
    )

    assert tab.project_combo.currentData() == seeded["project"].id
    assert tab._current_visible_panel_ids() == ["milestones", "watchlist", "register", "kpi"]
    assert tab._active_dashboard_panel_count() == 4
    assert tab.milestone_group.isHidden() is False
    assert tab.watchlist_group.isHidden() is False
    assert tab.register_group.isHidden() is False
    assert tab.kpi_group.isHidden() is False
    assert tab.milestone_table.rowCount() >= 2
    assert tab.watchlist_table.rowCount() >= 1
    assert tab.register_summary_label.rowCount() == 5
    assert tab.register_urgent_table.rowCount() >= 1
