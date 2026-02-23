def test_cost_items_and_summary(services):
    ps = services["project_service"]
    ts = services["task_service"]
    cost_s = services["cost_service"]

    project = ps.create_project("Cost Test", "")
    pid = project.id

    t1 = ts.create_task(pid, "Dev", duration_days=5)
    t2 = ts.create_task(pid, "QAT", duration_days=2)

    # Add project-level and task-level cost items
    c1 = cost_s.add_cost_item(pid, "License", planned_amount=500.0, task_id=None)
    c2 = cost_s.add_cost_item(pid, "Dev effort", planned_amount=2000.0, task_id=t1.id)
    c3 = cost_s.add_cost_item(pid, "QA effort", planned_amount=800.0, task_id=t2.id)

    # Update some actuals
    cost_s.update_cost_item(c2.id, actual_amount=2200.0)
    cost_s.update_cost_item(c3.id, actual_amount=700.0)

    summary = cost_s.get_project_cost_summary(pid)
    assert summary["items_count"] == 3
    assert summary["total_planned"] == 500.0 + 2000.0 + 800.0
    assert summary["total_actual"] == 2200.0 + 700.0
    assert summary["variance"] == summary["total_actual"] - summary["total_planned"]
