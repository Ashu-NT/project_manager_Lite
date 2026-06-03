from datetime import date

from src.core.shared.events.domain_events import domain_events


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

