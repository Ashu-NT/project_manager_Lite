from datetime import date
from core.models import TaskStatus


def test_task_progress_and_status_transitions(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Progress Test", "")
    pid = project.id

    t = ts.create_task(pid, "Task P", start_date=date(2023, 11, 6), duration_days=2)

    # Initially TODO
    assert t.status == TaskStatus.TODO

    # Start work
    t = ts.update_progress(t.id, percent_complete=10.0, actual_start=date(2023, 11, 6))
    assert t.status == TaskStatus.IN_PROGRESS
    assert t.actual_start == date(2023, 11, 6)

    # Finish
    t = ts.update_progress(t.id, percent_complete=100.0, actual_end=date(2023, 11, 7))
    assert t.status == TaskStatus.DONE
    assert t.actual_end == date(2023, 11, 7)


def test_task_progress_accepts_explicit_status_updates(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Progress Status Override", "")
    pid = project.id
    t = ts.create_task(pid, "Task S", start_date=date(2023, 11, 6), duration_days=2)

    t = ts.update_progress(t.id, status=TaskStatus.BLOCKED)
    assert t.status == TaskStatus.BLOCKED

    t = ts.update_progress(t.id, percent_complete=100.0, status=TaskStatus.BLOCKED)
    assert t.percent_complete == 100.0
    assert t.status == TaskStatus.BLOCKED
