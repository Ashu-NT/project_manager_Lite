from datetime import date

import pytest

from core.exceptions import BusinessRuleError
from core.models import DependencyType


def test_preview_resource_conflicts_detects_overallocation(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Leveling Preview", "")
    task_a = ts.create_task(project.id, "Task A", start_date=date(2024, 1, 1), duration_days=2)
    task_b = ts.create_task(project.id, "Task B", start_date=date(2024, 1, 5), duration_days=2)
    resource = rs.create_resource("Shared Dev", "Developer", hourly_rate=100.0)

    ts.assign_resource(task_a.id, resource.id, allocation_percent=70.0)
    ts.assign_resource(task_b.id, resource.id, allocation_percent=50.0)
    ts.update_task(task_b.id, start_date=date(2024, 1, 1), duration_days=2)

    conflicts = sched.preview_resource_conflicts(project.id)
    assert conflicts
    first = conflicts[0]
    assert first.resource_id == resource.id
    assert first.resource_name == "Shared Dev"
    assert first.total_allocation_percent == pytest.approx(120.0)
    assert {entry.task_name for entry in first.entries} == {"Task A", "Task B"}


def test_auto_level_resources_reduces_conflicts(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Auto Level", "")
    task_a = ts.create_task(project.id, "Task A", start_date=date(2024, 1, 1), duration_days=2)
    task_b = ts.create_task(project.id, "Task B", start_date=date(2024, 1, 5), duration_days=2)
    resource = rs.create_resource("Auto Shared", "Developer", hourly_rate=110.0)

    ts.assign_resource(task_a.id, resource.id, allocation_percent=70.0)
    ts.assign_resource(task_b.id, resource.id, allocation_percent=50.0)
    ts.update_task(task_b.id, start_date=date(2024, 1, 1), duration_days=2)

    before = sched.preview_resource_conflicts(project.id)
    result = sched.auto_level_resources(project.id, max_iterations=10)
    after = sched.preview_resource_conflicts(project.id)

    assert before
    assert result.conflicts_before == len(before)
    assert result.conflicts_after == len(after)
    assert result.actions
    assert len(after) < len(before)


def test_manual_resource_leveling_rejects_task_with_successors(services):
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Manual Level Guard", "")
    task_a = ts.create_task(project.id, "Task Alpha", start_date=date(2024, 1, 1), duration_days=2)
    task_b = ts.create_task(project.id, "Task Beta", duration_days=2)
    ts.add_dependency(task_a.id, task_b.id, DependencyType.FINISH_TO_START, lag_days=0)

    with pytest.raises(BusinessRuleError) as exc:
        sched.resolve_resource_conflict_manual(project.id, task_a.id, shift_working_days=1)
    assert exc.value.code == "RESOURCE_LEVELING_DEPENDENCY_BLOCK"


def test_manual_resource_leveling_shifts_leaf_task_dates(services):
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]
    wc = services["work_calendar_engine"]

    project = ps.create_project("Manual Level Shift", "")
    task = ts.create_task(project.id, "Task Leaf", start_date=date(2024, 1, 1), duration_days=3)
    old_start = task.start_date
    old_end = task.end_date

    action = sched.resolve_resource_conflict_manual(
        project.id,
        task.id,
        shift_working_days=2,
        reason="User selected move",
    )
    updated = next(t for t in ts.list_tasks_for_project(project.id) if t.id == task.id)

    assert action.task_id == task.id
    assert action.shift_working_days == 2
    assert action.old_start == old_start
    assert action.old_end == old_end
    assert action.new_start == wc.add_working_days(old_start, 3)
    assert updated.start_date == action.new_start
    assert updated.end_date == action.new_end
