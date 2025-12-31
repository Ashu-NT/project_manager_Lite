from datetime import date
from core.exceptions import BusinessRuleError


def test_resource_assignment_and_overload(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Res Test", "")
    pid = project.id

    # Create tasks with overlapping periods
    t1 = ts.create_task(pid, "Task 1", start_date=date(2023, 11, 6), duration_days=3)
    t2 = ts.create_task(pid, "Task 2", start_date=date(2023, 11, 7), duration_days=3)

    # Create resource
    r = rs.create_resource("Dev 1", "Developer", hourly_rate=100.0)

    # Assign 50% to t1
    a1 = ts.assign_resource(t1.id, r.id, allocation_percent=50.0)
    assert a1.allocation_percent == 50.0

    # Assign another 40% on overlapping task -> should be OK (total 90%)
    a2 = ts.assign_resource(t2.id, r.id, allocation_percent=40.0)
    assert a2.allocation_percent == 40.0

    # Now try to assign 20% on overlapping task -> should fail with overload
    try:
        ts.assign_resource(t2.id, r.id, allocation_percent=20.0)
        assert False, "Expected BusinessRuleError for over-allocation"
    except BusinessRuleError:
        pass

    # Check tasks for resource in project
    tasks_for_res = ts.query_tasks(project_id=pid, resource_id=r.id)
    assert len(tasks_for_res) == 2