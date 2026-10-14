from datetime import date


def test_project_delete_cascade(services):
    services['project_query']
    services['task_lookup_query']
    project = services['project_create'].create_project("Delete Test", "")
    pid = project.id

    # Create task, resource, and assignment.
    t = services['task_lifecycle_commands'].create_task(pid, "Task 1", start_date=date(2023, 11, 6), duration_days=2)
    r = services["resource_master_commands"].create_resource("Dev", "Developer", hourly_rate=100.0)
    services['task_assignment_commands'].assign_resource(t.id, r.id, allocation_percent=50.0)

    # Confirm they exist in DB
    assert services['task_lookup_query'].list_tasks_for_project(pid)
    assert services["resource_query"].list_resources()

    # Delete project
    services['project_deletion'].delete_project(pid)

    # Tasks gone
    assert services['task_lookup_query'].list_tasks_for_project(pid) == []

    # Resource still exists (we decided project delete does not delete resources globally)
    assert services["resource_query"].list_resources()

