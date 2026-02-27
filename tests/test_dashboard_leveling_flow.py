from datetime import date
from pathlib import Path

from core.events.domain_events import domain_events


def test_dashboard_service_preview_resource_conflicts(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    ds = services["dashboard_service"]

    project = ps.create_project("Dashboard Conflict Preview", "")
    t1 = ts.create_task(project.id, "Task A", start_date=date(2024, 2, 1), duration_days=2)
    t2 = ts.create_task(project.id, "Task B", start_date=date(2024, 2, 8), duration_days=2)
    res = rs.create_resource("Planner", "PM", hourly_rate=100.0)

    ts.assign_resource(t1.id, res.id, allocation_percent=70.0)
    ts.assign_resource(t2.id, res.id, allocation_percent=50.0)
    ts.update_task(t2.id, start_date=date(2024, 2, 1), duration_days=2)

    conflicts = ds.preview_resource_conflicts(project.id)
    assert conflicts
    assert conflicts[0].resource_name == "Planner"
    assert conflicts[0].total_allocation_percent > 100.0


def test_dashboard_service_auto_level_overallocations(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    ds = services["dashboard_service"]

    project = ps.create_project("Dashboard Auto Level", "")
    t1 = ts.create_task(project.id, "Task A", start_date=date(2024, 2, 1), duration_days=2)
    t2 = ts.create_task(project.id, "Task B", start_date=date(2024, 2, 8), duration_days=2)
    res = rs.create_resource("Shared", "Dev", hourly_rate=120.0)

    ts.assign_resource(t1.id, res.id, allocation_percent=70.0)
    ts.assign_resource(t2.id, res.id, allocation_percent=50.0)
    ts.update_task(t2.id, start_date=date(2024, 2, 1), duration_days=2)

    before = ds.preview_resource_conflicts(project.id)
    result = ds.auto_level_overallocations(project.id, max_iterations=20)
    after = ds.preview_resource_conflicts(project.id)

    assert before
    assert result.conflicts_before == len(before)
    assert len(result.actions) >= 1
    assert len(after) <= len(before)


def test_dashboard_service_auto_level_emits_tasks_changed_event(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    ds = services["dashboard_service"]

    project = ps.create_project("Dashboard Auto Level Event", "")
    t1 = ts.create_task(project.id, "Task A", start_date=date(2024, 2, 1), duration_days=2)
    t2 = ts.create_task(project.id, "Task B", start_date=date(2024, 2, 8), duration_days=2)
    res = rs.create_resource("Shared Event", "Dev", hourly_rate=120.0)

    ts.assign_resource(t1.id, res.id, allocation_percent=70.0)
    ts.assign_resource(t2.id, res.id, allocation_percent=50.0)
    ts.update_task(t2.id, start_date=date(2024, 2, 1), duration_days=2)

    seen: list[str] = []

    def _on_tasks_changed(project_id: str) -> None:
        seen.append(project_id)

    domain_events.tasks_changed.connect(_on_tasks_changed)
    try:
        result = ds.auto_level_overallocations(project.id, max_iterations=20)
    finally:
        domain_events.tasks_changed.disconnect(_on_tasks_changed)

    assert result.actions
    assert project.id in seen


def test_dashboard_service_manual_shift_emits_tasks_changed_event(services):
    ps = services["project_service"]
    ts = services["task_service"]
    ds = services["dashboard_service"]

    project = ps.create_project("Dashboard Manual Shift Event", "")
    task = ts.create_task(project.id, "Leaf Task", start_date=date(2024, 2, 1), duration_days=2)

    seen: list[str] = []

    def _on_tasks_changed(project_id: str) -> None:
        seen.append(project_id)

    domain_events.tasks_changed.connect(_on_tasks_changed)
    try:
        ds.manually_shift_task_for_leveling(project.id, task.id, shift_working_days=1)
    finally:
        domain_events.tasks_changed.disconnect(_on_tasks_changed)

    assert project.id in seen


def test_dashboard_tab_wires_leveling_actions_and_conflict_grid():
    root = Path(__file__).resolve().parents[1]
    tab_text = (root / "ui" / "dashboard" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    actions_text = (root / "ui" / "dashboard" / "workqueue_actions.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    ops_text = (root / "ui" / "dashboard" / "leveling_ops.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    panel_text = (root / "ui" / "dashboard" / "alerts_panel.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    service_text = (root / "core" / "services" / "dashboard" / "service.py").read_text(encoding="utf-8", errors="ignore")

    assert 'self.btn_preview_conflicts = QPushButton("Preview Conflicts")' in panel_text
    assert 'self.btn_auto_level = QPushButton("Auto-Level")' in panel_text
    assert 'self.btn_manual_shift = QPushButton("Manual Shift")' in panel_text
    assert "self.btn_preview_conflicts.setToolTip(" in panel_text
    assert "self.btn_auto_level.setToolTip(" in panel_text
    assert "self.btn_manual_shift.setToolTip(" in panel_text
    assert "self.conflicts_table = QTableWidget(0, 4)" in panel_text
    assert "DashboardQueueButton(\"Conflicts\", active_variant=\"danger\")" in tab_text
    assert "DashboardQueueButton(\"Alerts\", active_variant=\"warning\")" in tab_text
    assert "DashboardQueueButton(\"Upcoming\", active_variant=\"info\")" in tab_text
    assert "self.btn_open_conflicts.clicked.connect(self._open_conflicts_dialog)" in tab_text
    assert "self.btn_open_alerts.clicked.connect(self._open_alerts_dialog)" in tab_text
    assert "self.btn_open_upcoming.clicked.connect(self._open_upcoming_dialog)" in tab_text
    assert "self.upcoming_table = QTableWidget(" not in tab_text
    assert "def _prepare_conflicts_dialog" in actions_text
    assert "self.btn_auto_level.clicked.connect(self._auto_level_conflicts)" in actions_text
    assert "self.btn_manual_shift.clicked.connect(self._manual_shift_selected_conflict)" in actions_text

    assert "def _preview_conflicts" in ops_text
    assert "def _auto_level_conflicts" in ops_text
    assert "def _manual_shift_selected_conflict" in ops_text
    assert "self.btn_open_conflicts.setText(" in ops_text
    assert "self._update_conflicts_from_load(overloaded)" in ops_text
    assert "Date shifts:" in ops_text
    assert "No eligible task was shifted." in ops_text
    assert "Iterations used:" in ops_text

    assert "def preview_resource_conflicts" in service_text
    assert "def auto_level_overallocations" in service_text
    assert "domain_events.tasks_changed.emit(project_id)" in service_text
    rendering_alerts_text = (root / "ui" / "dashboard" / "rendering_alerts.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    rendering_charts_text = (root / "ui" / "dashboard" / "rendering_charts.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "def _update_conflicts_from_load" in rendering_alerts_text
    assert "self.btn_open_alerts.set_badge(" in rendering_alerts_text
    assert "self.btn_open_upcoming.set_badge(" in rendering_charts_text
