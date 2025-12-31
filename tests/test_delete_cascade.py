from datetime import date


def test_project_delete_cascade(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    cost_s = services["cost_service"]
    cs = services["calendar_service"]
    session = services["session"]

    project = ps.create_project("Delete Test", "")
    pid = project.id

    # Create task, resource, assignment, cost, event
    t = ts.create_task(pid, "Task 1", start_date=date(2023, 11, 6), duration_days=2)
    r = rs.create_resource("Dev", "Developer", 100.0)
    a = ts.assign_resource(t.id, r.id, allocation_percent=50.0)
    cost = cost_s.add_cost_item(pid, "Cost 1", planned_amount=100.0, task_id=t.id)
    event = cs.sync_task_to_calendar(t)

    # Confirm they exist in DB
    assert ts.list_tasks_for_project(pid)
    assert rs.list_resources()
    assert cost_s.list_cost_items_for_project(pid)
    if event:
        events = cs.list_events_for_project(pid)
        assert events

    # Delete project
    ps.delete_project(pid)

    # Tasks gone
    assert ts.list_tasks_for_project(pid) == []

    # Cost items by project should be gone
    assert cost_s.list_cost_items_for_project(pid) == []

    # Calendar events for project should be gone
    assert cs.list_events_for_project(pid) == []

    # Resource still exists (we decided project delete does not delete resources globally)
    assert rs.list_resources()