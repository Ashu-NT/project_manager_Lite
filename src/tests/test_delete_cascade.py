from datetime import date


def test_project_delete_cascade(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Delete Test", "")
    pid = project.id

    # Create task, resource, and assignment.
    t = ts.create_task(pid, "Task 1", start_date=date(2023, 11, 6), duration_days=2)
    r = rs.create_resource("Dev", "Developer", 100.0)
    ts.assign_resource(t.id, r.id, allocation_percent=50.0)

    # Confirm they exist in DB
    assert ts.list_tasks_for_project(pid)
    assert rs.list_resources()

    # Delete project
    ps.delete_project(pid)

    # Tasks gone
    assert ts.list_tasks_for_project(pid) == []

    # Resource still exists (we decided project delete does not delete resources globally)
    assert rs.list_resources()

