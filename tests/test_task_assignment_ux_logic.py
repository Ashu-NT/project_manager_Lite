from datetime import date

import pytest

from ui.task.assignment_summary import build_task_assignment_summary


def test_build_task_assignment_summary_aggregates_count_alloc_and_hours(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Assignment Summary", "")
    task_a = ts.create_task(project.id, "Task A", start_date=date(2024, 1, 1), duration_days=2)
    task_b = ts.create_task(project.id, "Task B", start_date=date(2024, 1, 1), duration_days=2)

    r1 = rs.create_resource("Res 1", "Dev", hourly_rate=100.0)
    r2 = rs.create_resource("Res 2", "QA", hourly_rate=90.0)

    a1 = ts.assign_resource(task_a.id, r1.id, allocation_percent=30.0)
    a2 = ts.assign_resource(task_a.id, r2.id, allocation_percent=50.0)
    ts.set_assignment_hours(a1.id, 4.0)
    ts.set_assignment_hours(a2.id, 6.0)

    assignments = ts.list_assignments_for_tasks([task_a.id, task_b.id])
    summary = build_task_assignment_summary([task_a.id, task_b.id], assignments)

    assert summary[task_a.id] == (2, 80.0, 10.0)
    assert summary[task_b.id] == (0, 0.0, 0.0)


def test_set_assignment_allocation_updates_and_enforces_overallocation(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Allocation Edit Rules", "")
    t1 = ts.create_task(project.id, "Task One", start_date=date(2024, 1, 1), duration_days=3)
    t2 = ts.create_task(project.id, "Task Two", start_date=date(2024, 1, 1), duration_days=3)
    res = rs.create_resource("Shared Resource", "Dev", hourly_rate=120.0)

    a1 = ts.assign_resource(t1.id, res.id, allocation_percent=60.0)
    a2 = ts.assign_resource(t2.id, res.id, allocation_percent=30.0)

    updated = ts.set_assignment_allocation(a2.id, 40.0)
    assert updated.allocation_percent == pytest.approx(40.0)

    warned = ts.set_assignment_allocation(a2.id, 50.0)
    assert warned.allocation_percent == pytest.approx(50.0)

    warning_text = ts.consume_last_overallocation_warning()
    assert warning_text is not None
    assert "over-allocated on" in warning_text
    assert ts.consume_last_overallocation_warning() is None

    unchanged = ts.get_assignment(a1.id)
    assert unchanged is not None
    assert unchanged.allocation_percent == pytest.approx(60.0)

    conflicts = sched.preview_resource_conflicts(project.id)
    assert conflicts
    assert conflicts[0].total_allocation_percent > 100.0
