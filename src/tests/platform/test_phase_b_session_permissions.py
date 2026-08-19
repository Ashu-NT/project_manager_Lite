from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.core.platform.common.exceptions import BusinessRuleError


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
    reporting = services["reporting_service"]
    finance = services["finance_service"]
    dashboard = services["dashboard_service"]
    approvals = services["approval_service"]
    audit = services["enterprise_audit_service"]

    project = ps.create_project("Read Permission Project")
    task = ts.create_task(project.id, "Read Permission Task", start_date=date(2026, 5, 1), duration_days=2)
    resource = rs.create_resource("Read Permission Resource", hourly_rate=120.0)

    services["user_session"].clear()

    with pytest.raises(BusinessRuleError):
        ps.list_projects()
    with pytest.raises(BusinessRuleError):
        ts.list_tasks_for_project(project.id)
    with pytest.raises(BusinessRuleError):
        rs.list_resources()
    with pytest.raises(BusinessRuleError):
        reporting.get_project_kpis(project.id)
    with pytest.raises(BusinessRuleError):
        finance.get_finance_snapshot(project.id)
    with pytest.raises(BusinessRuleError):
        dashboard.get_dashboard_data(project.id)
    with pytest.raises(BusinessRuleError, match="approval.request"):
        approvals.list_requests(project_id=project.id)
    with pytest.raises(BusinessRuleError, match="audit.read"):
        audit.list_recent()


def test_viewer_cannot_manage_resources_costs_tasks_or_assignments(services):
    auth = services["auth_service"]
    auth.register_user("viewer2", "StrongPass123", role_names=["viewer"])
    target = auth.register_user("reset-target-viewer", "StrongPass123", role_names=["viewer"])
    _login_as(services, "admin", "ChangeMe123!")

    ps = services["project_service"]
    rs = services["resource_service"]
    ts = services["task_service"]
    cost_entries = services["cost_entry_service"]
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
        cost_entries.create_manual_entry(
            project_id=project.id,
            command_id="viewer-forbidden-cost",
            description="Forbidden cost",
            amount=Decimal("100"),
            currency_code="EUR",
            transaction_date=date(2026, 1, 1),
            cost_code_id="forbidden-cost-code",
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
    ecs = services["enterprise_calendar_service"]
    ds = services["dashboard_service"]

    project = ps.create_project("Ops permission project")
    resource = rs.create_resource("Ops resource", hourly_rate=100.0)
    project_resource = prs.add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        planned_hours=16.0,
    )

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
        ecs.create_calendar(
            name="Viewer Calendar",
            code="VIEWER_CAL",
            calendar_type="standard",
        )


def test_governance_permissions_are_split_between_request_and_decide(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "project_cost.approve")
    auth = services["auth_service"]
    auth.register_user("planner4", "StrongPass123", role_names=["planner"])
    auth.register_user("viewer4", "StrongPass123", role_names=["viewer"])
    _login_as(services, "admin", "ChangeMe123!")

    ps = services["project_service"]
    cost_entries = services["cost_entry_service"]
    configuration = services["financial_configuration_service"]
    approvals = services["approval_service"]

    project = ps.create_project("Governance permission split")
    organization = services["organization_service"].get_active_organization()
    cost_code = configuration.create_cost_code(code="HOTEL", name="Hotel")
    item = cost_entries.create_manual_entry(
        project_id=project.id,
        command_id="governance-permission-split",
        description="Hotel",
        amount=Decimal("20"),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 1, 1),
        cost_code_id=cost_code.id,
    )
    item = cost_entries.submit(item.id, expected_version=item.row_version)
    _login_as(services, "planner4", "StrongPass123")
    result = cost_entries.approve(item.id, expected_version=item.row_version)
    assert result.outcome.value == "pending_approval"
    request_id = approvals.list_pending(project_id=project.id)[0].id

    _login_as(services, "viewer4", "StrongPass123")
    with pytest.raises(BusinessRuleError, match="approval.request"):
        cost_entries.approve(item.id, expected_version=item.row_version)
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
        ts.approve_timesheet_period(submitted.period_id)

    with pytest.raises(BusinessRuleError, match="timesheet.lock"):
        ts.lock_timesheet_period(resource.id, period_start=date(2026, 7, 1))

    _login_as(services, "viewer-timesheet", "StrongPass123")
    with pytest.raises(BusinessRuleError, match="timesheet.submit"):
        ts.submit_timesheet_period(resource.id, period_start=date(2026, 6, 1))


def test_shared_time_permission_aliases_allow_time_queries_and_edits(services):
    ps = services["project_service"]
    rs = services["resource_service"]
    ts = services["task_service"]
    timesheet_service = services["timesheet_service"]
    user_session = services["user_session"]

    project = ps.create_project("Shared Time Permission Alias")
    task = ts.create_task(project.id, "Alias Permission Task", start_date=date(2026, 7, 1), duration_days=2)
    resource = rs.create_resource("Alias Logger", hourly_rate=100.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)
    first = timesheet_service.add_time_entry(
        assignment.id,
        entry_date=date(2026, 7, 1),
        hours=2.0,
        note="Admin seed entry",
    )
    active_tenant_id = user_session.active_tenant_id()
    active_organization_id = user_session.active_organization_id()

    user_session.set_validator(None)
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="u-time-read",
            username="time-reader",
            display_name="Time Reader",
            role_names=frozenset({"time_reader"}),
            permissions=frozenset({"time.read"}),
            active_tenant_id=active_tenant_id,
            active_organization_id=active_organization_id,
        )
    )
    visible = timesheet_service.list_time_entries_for_assignment(assignment.id)
    assert [row.id for row in visible] == [first.id]

    user_session.set_principal(
        UserSessionPrincipal(
            user_id="u-time-manage",
            username="time-manager",
            display_name="Time Manager",
            role_names=frozenset({"time_manager"}),
            permissions=frozenset({"time.manage", "time.read"}),
            active_tenant_id=active_tenant_id,
            active_organization_id=active_organization_id,
        )
    )
    second = timesheet_service.add_work_entry(
        assignment.id,
        entry_date=date(2026, 7, 2),
        hours=3.5,
        note="Shared manage permission entry",
    )
    assert second.work_allocation_id == assignment.id
    assert len(timesheet_service.list_time_entries_for_work_allocation(assignment.id)) == 2

