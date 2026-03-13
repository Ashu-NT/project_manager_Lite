from __future__ import annotations

from datetime import date

import pytest

from core.exceptions import BusinessRuleError


def _login_as(services, username: str, password: str):
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def test_user_session_enforces_manage_permissions(services):
    auth = services["auth_service"]
    auth.register_user("viewer1", "StrongPass123", role_names=["viewer"])
    _login_as(services, "viewer1", "StrongPass123")

    ps = services["project_service"]
    with pytest.raises(BusinessRuleError, match="Permission denied"):
        ps.create_project("Forbidden project")


def test_admin_session_can_execute_manage_operations(services):
    _login_as(services, "admin", "ChangeMe123!")

    ps = services["project_service"]
    p = ps.create_project("Allowed project")
    assert p.id


def test_cleared_session_denies_core_read_models(services):
    _login_as(services, "admin", "ChangeMe123!")

    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    cs = services["cost_service"]
    reporting = services["reporting_service"]
    finance = services["finance_service"]
    dashboard = services["dashboard_service"]
    approvals = services["approval_service"]
    audit = services["audit_service"]
    calendar = services["calendar_service"]

    project = ps.create_project("Read Permission Project")
    task = ts.create_task(project.id, "Read Permission Task", start_date=date(2026, 5, 1), duration_days=2)
    resource = rs.create_resource("Read Permission Resource", hourly_rate=120.0)
    cs.add_cost_item(project.id, "Read Permission Cost", planned_amount=100.0)
    calendar.sync_task_to_calendar(task)

    services["user_session"].clear()

    with pytest.raises(BusinessRuleError, match="project.read"):
        ps.list_projects()
    with pytest.raises(BusinessRuleError, match="task.read"):
        ts.list_tasks_for_project(project.id)
    with pytest.raises(BusinessRuleError, match="resource.read"):
        rs.list_resources()
    with pytest.raises(BusinessRuleError, match="cost.read"):
        cs.list_cost_items_for_project(project.id)
    with pytest.raises(BusinessRuleError, match="report.view"):
        reporting.get_project_kpis(project.id)
    with pytest.raises(BusinessRuleError, match="report.view"):
        finance.get_finance_snapshot(project.id)
    with pytest.raises(BusinessRuleError, match="report.view"):
        dashboard.get_dashboard_data(project.id)
    with pytest.raises(BusinessRuleError, match="approval.request"):
        approvals.list_requests(project_id=project.id)
    with pytest.raises(BusinessRuleError, match="audit.read"):
        audit.list_recent(project_id=project.id)
    with pytest.raises(BusinessRuleError, match="task.read"):
        calendar.list_events_for_project(project.id)


def test_viewer_cannot_manage_resources_costs_tasks_or_assignments(services):
    auth = services["auth_service"]
    auth.register_user("viewer2", "StrongPass123", role_names=["viewer"])
    target = auth.register_user("reset-target-viewer", "StrongPass123", role_names=["viewer"])
    _login_as(services, "admin", "ChangeMe123!")

    ps = services["project_service"]
    rs = services["resource_service"]
    ts = services["task_service"]
    cs = services["cost_service"]
    prs = services["project_resource_service"]

    project = ps.create_project("Permission project")
    resource = rs.create_resource("Assigned Resource", hourly_rate=120.0)
    project_resource = prs.add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        planned_hours=40.0,
    )
    task = ts.create_task(project_id=project.id, name="Permission task")
    assignment = ts.assign_project_resource(task.id, project_resource.id, 50.0)

    _login_as(services, "viewer2", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        auth.reset_user_password(target.id, "ResetByViewer123")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        rs.create_resource("Forbidden resource")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        cs.add_cost_item(
            project_id=project.id,
            description="Forbidden cost",
            planned_amount=100.0,
        )

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        ts.create_task(project_id=project.id, name="Forbidden task")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        ts.set_assignment_allocation(assignment.id, 40.0)

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        ts.set_assignment_hours(assignment.id, 2.0)

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        ts.unassign_resource(assignment.id)


def test_viewer_cannot_manage_project_resources_or_calendar_or_leveling(services):
    auth = services["auth_service"]
    auth.register_user("viewer3", "StrongPass123", role_names=["viewer"])
    _login_as(services, "admin", "ChangeMe123!")

    ps = services["project_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    wcs = services["work_calendar_service"]
    ds = services["dashboard_service"]

    project = ps.create_project("Ops permission project")
    resource = rs.create_resource("Ops resource", hourly_rate=100.0)
    project_resource = prs.add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        planned_hours=16.0,
    )
    holiday = wcs.add_holiday(date(2026, 1, 1), "New Year")

    _login_as(services, "viewer3", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        prs.add_to_project(
            project_id=project.id,
            resource_id=resource.id,
            planned_hours=8.0,
        )

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        prs.update(
            pr_id=project_resource.id,
            hourly_rate=80.0,
            currency_code="EUR",
            planned_hours=20.0,
            is_active=True,
        )

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        prs.set_active(project_resource.id, False)

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        prs.delete(project_resource.id)

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        wcs.set_working_days({0, 1, 2, 3, 4}, hours_per_day=8.0)

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        wcs.add_holiday(date(2026, 1, 2), "Another holiday")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        wcs.delete_holiday(holiday.id)

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        ds.auto_level_overallocations(project.id, max_iterations=1)

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        ds.manually_shift_task_for_leveling(
            project_id=project.id,
            task_id="missing-task",
            shift_working_days=1,
        )


def test_governance_permissions_are_split_between_request_and_decide(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "cost.update")
    auth = services["auth_service"]
    auth.register_user("planner4", "StrongPass123", role_names=["planner"])
    auth.register_user("viewer4", "StrongPass123", role_names=["viewer"])
    _login_as(services, "admin", "ChangeMe123!")

    ps = services["project_service"]
    cs = services["cost_service"]
    approvals = services["approval_service"]

    project = ps.create_project("Governance permission split")
    item = cs.add_cost_item(project.id, "Hotel", planned_amount=200.0, actual_amount=20.0)
    _login_as(services, "planner4", "StrongPass123")
    with pytest.raises(BusinessRuleError, match="Approval required"):
        cs.update_cost_item(item.id, actual_amount=25.0)
    request_id = approvals.list_pending(project_id=project.id)[0].id

    _login_as(services, "viewer4", "StrongPass123")
    with pytest.raises(BusinessRuleError, match="approval.request"):
        cs.update_cost_item(item.id, actual_amount=30.0)
    with pytest.raises(BusinessRuleError, match="approval.decide"):
        approvals.approve_and_apply(request_id)


def test_timesheet_period_permissions_are_split_between_submit_approve_and_lock(services):
    auth = services["auth_service"]
    auth.register_user("planner-timesheet", "StrongPass123", role_names=["planner"])
    auth.register_user("viewer-timesheet", "StrongPass123", role_names=["viewer"])
    _login_as(services, "admin", "ChangeMe123!")

    ps = services["project_service"]
    rs = services["resource_service"]
    ts = services["task_service"]

    project = ps.create_project("Timesheet Permission Split")
    task = ts.create_task(project.id, "Timesheet Permission Task", start_date=date(2026, 6, 1), duration_days=2)
    resource = rs.create_resource("Planner Logger", hourly_rate=100.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)
    ts.add_time_entry(
        assignment.id,
        entry_date=date(2026, 6, 2),
        hours=5.0,
        note="Initial work",
    )

    _login_as(services, "planner-timesheet", "StrongPass123")
    submitted = ts.submit_timesheet_period(resource.id, period_start=date(2026, 6, 9))
    assert submitted.status.value == "SUBMITTED"

    with pytest.raises(BusinessRuleError, match="timesheet.approve"):
        ts.approve_timesheet_period(submitted.id)

    with pytest.raises(BusinessRuleError, match="timesheet.lock"):
        ts.lock_timesheet_period(resource.id, period_start=date(2026, 7, 1))

    _login_as(services, "viewer-timesheet", "StrongPass123")
    with pytest.raises(BusinessRuleError, match="task.manage"):
        ts.submit_timesheet_period(resource.id, period_start=date(2026, 6, 1))
