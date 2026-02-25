from datetime import date, timedelta
from pathlib import Path

from core.exceptions import NotFoundError
from infra.db.repositories import SqlAlchemyAssignmentRepository, SqlAlchemyDependencyRepository
from ui.styles.theme import base_stylesheet
from ui.styles.theme import set_theme_mode
from ui.styles.theme import table_stylesheet
from ui.styles.ui_config import UIConfig as CFG


def test_cost_summary_has_legacy_and_normalized_keys(services):
    ps = services["project_service"]
    ts = services["task_service"]
    cost_s = services["cost_service"]

    project = ps.create_project("Cost Summary Keys", "")
    pid = project.id

    task = ts.create_task(pid, "Cost Task", duration_days=1)
    cost_s.add_cost_item(
        project_id=pid,
        description="One item",
        planned_amount=100.0,
        committed_amount=20.0,
        actual_amount=10.0,
        task_id=task.id,
    )

    summary = cost_s.get_project_cost_summary(pid)

    assert summary["total_planned"] == 100.0
    assert summary["total_committed"] == 20.0
    assert summary["total-committed"] == 20.0
    assert summary["total_actual"] == 10.0
    assert summary["variance"] == -90.0
    assert summary["variance_actual"] == -90.0
    assert summary["variance_commitment"] == -80.0
    assert summary["variance_committment"] == -80.0


def test_dashboard_high_priority_without_deadline_does_not_crash(services):
    ps = services["project_service"]
    ts = services["task_service"]
    ds = services["dashboard_service"]

    project = ps.create_project("Dashboard Priority", "")
    pid = project.id

    ts.create_task(
        pid,
        "High Priority No Deadline",
        start_date=date(2023, 11, 6),
        duration_days=2,
        priority=90,
    )

    data = ds.get_dashboard_data(pid)
    assert data.kpi.project_id == pid
    assert not any("High-priority task" in msg for msg in data.alerts)


def test_dashboard_upcoming_populates_main_resource_name(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    ds = services["dashboard_service"]

    project = ps.create_project("Dashboard Main Resource", "")
    pid = project.id

    task = ts.create_task(
        pid,
        "Upcoming Task",
        start_date=date.today() + timedelta(days=1),
        duration_days=2,
    )
    resource = rs.create_resource("Planned Engineer", "Developer", hourly_rate=100.0)
    ts.assign_resource(task.id, resource.id, allocation_percent=60.0)

    data = ds.get_dashboard_data(pid)
    rows = [row for row in data.upcoming_tasks if row.task_id == task.id]

    assert rows
    assert rows[0].main_resource == "Planned Engineer"


def test_baseline_variance_marks_critical_tasks(services):
    ps = services["project_service"]
    ts = services["task_service"]
    baseline_s = services["baseline_service"]
    reporting_s = services["reporting_service"]

    project = ps.create_project("Variance Critical", "")
    pid = project.id

    t = ts.create_task(pid, "Only Task", start_date=date(2023, 11, 6), duration_days=2)
    baseline = baseline_s.create_baseline(pid, "B1")

    rows = reporting_s.get_baseline_schedule_variance(pid, baseline_id=baseline.id)
    assert len(rows) == 1
    assert rows[0].task_id == t.id
    assert rows[0].is_critical is True


def test_dependency_repository_filters_by_project(session, services):
    ps = services["project_service"]
    ts = services["task_service"]

    p1 = ps.create_project("Dep P1", "")
    p2 = ps.create_project("Dep P2", "")

    a1 = ts.create_task(p1.id, "A01", start_date=date(2023, 11, 6), duration_days=1)
    b1 = ts.create_task(p1.id, "B01", duration_days=1)
    a2 = ts.create_task(p2.id, "A02", start_date=date(2023, 11, 6), duration_days=1)
    b2 = ts.create_task(p2.id, "B02", duration_days=1)

    ts.add_dependency(a1.id, b1.id)
    ts.add_dependency(a2.id, b2.id)

    dep_repo = SqlAlchemyDependencyRepository(session)
    deps_p1 = dep_repo.list_by_project(p1.id)
    deps_p2 = dep_repo.list_by_project(p2.id)

    assert len(deps_p1) == 1
    assert len(deps_p2) == 1
    assert deps_p1[0].predecessor_task_id == a1.id
    assert deps_p2[0].predecessor_task_id == a2.id


def test_remove_dependency_raises_not_found(services):
    ts = services["task_service"]
    try:
        ts.remove_dependency("missing-dependency-id")
        assert False, "Expected NotFoundError for missing dependency"
    except NotFoundError as exc:
        assert exc.code == "DEPENDENCY_NOT_FOUND"


def test_assignment_repository_list_by_tasks_returns_domain_models(session, services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    p = ps.create_project("Assignment Mapping", "")
    t = ts.create_task(p.id, "Task A", start_date=date(2023, 11, 6), duration_days=2)
    r = rs.create_resource("Dev 1", "Developer", hourly_rate=100.0)
    created = ts.assign_resource(t.id, r.id, allocation_percent=50.0)

    repo = SqlAlchemyAssignmentRepository(session)
    rows = repo.list_by_tasks([t.id])

    assert len(rows) == 1
    assert rows[0].id == created.id
    assert rows[0].__class__.__name__ == "TaskAssignment"


def test_base_stylesheet_contains_calendar_overrides():
    css = base_stylesheet()
    assert "QCalendarWidget QTableView::item" in css
    assert "padding: 0px;" in css
    assert "QTableView::item:focus" in css
    assert "border: 2px solid" in css


def test_base_stylesheet_highlights_selected_tab_clearly():
    css = base_stylesheet()
    assert "QTabBar::tab:selected" in css
    assert "border-top: 3px solid" in css
    assert "QTabBar::tab:!selected" in css


def test_dark_theme_mode_updates_tokens_and_stylesheet():
    set_theme_mode("dark")
    css_dark = base_stylesheet()
    assert CFG.COLOR_BG_APP == "#0B1220"
    assert CFG.COLOR_BG_APP in css_dark
    assert "QMainWindow, QDialog" in css_dark

    set_theme_mode("light")
    css_light = base_stylesheet()
    assert CFG.COLOR_BG_APP == "#F4F7FB"
    assert CFG.COLOR_BG_APP in css_light


def test_dark_theme_info_and_meta_text_are_readable():
    set_theme_mode("dark")
    assert CFG.COLOR_TEXT_SECONDARY in CFG.INFO_TEXT_STYLE
    assert "font-size: 10pt" in CFG.INFO_TEXT_STYLE
    assert CFG.COLOR_TEXT_SECONDARY in CFG.DASHBOARD_KPI_SUB_STYLE


def test_table_stylesheet_includes_table_scrollbar_rules():
    set_theme_mode("light")
    css = table_stylesheet()
    assert "QTableView QScrollBar:vertical" in css
    assert "QTableView QScrollBar:horizontal" in css
    assert CFG.COLOR_SCROLLBAR_HANDLE in css
    assert CFG.COLOR_SCROLLBAR_TRACK in css


def test_main_window_wires_theme_switcher():
    text = (Path(__file__).resolve().parents[1] / "ui" / "main_window.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "self.theme_combo = QComboBox()" in text
    assert "def _on_theme_changed" in text
    assert "apply_app_style(app, mode=mode)" in text


def test_style_table_has_auto_fit_and_stronger_grid():
    text = (Path(__file__).resolve().parents[1] / "ui" / "styles" / "style_utils.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "def _fit_table_columns" in text
    assert "table.setShowGrid(True)" in text
    assert "table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in text
    assert "table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in text
    assert "_bind_auto_fit_signals(table)" in text


def test_cost_tab_removes_duplicate_budget_insights_panel():
    text = (Path(__file__).resolve().parents[1] / "ui" / "cost" / "tab.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert 'QGroupBox("Budget Insights")' not in text
    assert "self.lbl_budget_summary" not in text


def test_cost_tab_has_filter_row_and_committed_kpi():
    root = Path(__file__).resolve().parents[1]
    tab_text = (root / "ui" / "cost" / "tab.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    layout_text = (root / "ui" / "cost" / "layout.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert 'committed_card, self.lbl_kpi_committed = _kpi_card("Committed")' in tab_text
    assert "self.filter_text = QLineEdit()" in layout_text
    assert 'self.filter_type_combo.addItem("All Types", userData="")' in layout_text
    assert 'self.filter_task_combo.addItem("All Tasks", userData="")' in layout_text


def test_no_table_forces_horizontal_scrollbar_off():
    text = (Path(__file__).resolve().parents[1] / "ui" / "task" / "assignment_panel.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "ScrollBarAlwaysOff" not in text


def test_cost_labor_snapshot_uses_content_sized_columns():
    text = (Path(__file__).resolve().parents[1] / "ui" / "cost" / "labor_summary.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "for col in range(self.tbl_labor_summary.columnCount()):" in text
    assert "header.setSectionResizeMode(col, QHeaderView.ResizeToContents)" in text


def test_dashboard_and_report_tabs_surface_cost_source_transparency():
    root = Path(__file__).resolve().parents[1]
    dashboard_text = (root / "ui" / "dashboard" / "rendering_summary.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    kpi_text = (root / "ui" / "report" / "dialog_kpi.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    perf_text = (root / "ui" / "report" / "dialog_performance.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "Direct Cost" in dashboard_text
    assert "Computed Labor" in dashboard_text
    assert "Labor Adjustment" in dashboard_text
    assert "get_project_cost_source_breakdown" in kpi_text
    assert "get_project_cost_source_breakdown" in perf_text


def test_reporting_export_api_wires_cost_source_context():
    text = (Path(__file__).resolve().parents[1] / "core" / "reporting" / "api.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "get_project_cost_source_breakdown" in text
    assert "cost_sources=" in text
