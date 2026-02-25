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


def test_viewer_cannot_manage_resources_costs_tasks_or_assignments(services):
    auth = services["auth_service"]
    auth.register_user("viewer2", "StrongPass123", role_names=["viewer"])
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
