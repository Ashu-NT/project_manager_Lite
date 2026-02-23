from datetime import date

from ui.task.assignment_models import _assignment_hours_logged


def test_single_task_and_multi_task_assignment_queries_are_consistent(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Panel Consistency", "")
    task = ts.create_task(project.id, "Task", start_date=date(2024, 2, 1), duration_days=2)
    resource = rs.create_resource("Resource", "Dev", hourly_rate=100.0)

    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=55.0)
    ts.set_assignment_hours(assignment.id, 9.25)

    single = ts.list_assignments_for_task(task.id)
    multi = ts.list_assignments_for_tasks([task.id])

    assert len(single) == 1
    assert len(multi) == 1
    assert single[0].id == multi[0].id
    assert _assignment_hours_logged(single[0]) == 9.25
    assert _assignment_hours_logged(multi[0]) == 9.25

