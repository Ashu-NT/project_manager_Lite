from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth.session import UserSessionPrincipal


def _login_as(services, username: str, password: str):
    user_session = services["user_session"]
    user = services["authentication"].authenticate(username, password)
    user_session.set_principal(services["principal_builder"].build(user))


def test_user_session_enforces_manage_permissions(services):
    services["user_registration"].register_user(
        "viewer1", "StrongPass123", role_names=["viewer"]
    )
    _login_as(services, "viewer1", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services['project_create'].create_project("Forbidden project")


def test_admin_session_can_execute_manage_operations(services):
    _login_as(services, "admin", "ChangeMe123!")

    p = services['project_create'].create_project("Allowed project")
    assert p.id


def test_cleared_session_denies_core_read_models(services):
    _login_as(services, "admin", "ChangeMe123!")

    finance = services["finance_snapshot_query"]
    services["approval_commands"]
    audit = services["enterprise_audit_service"]

    project = services['project_create'].create_project("Read Permission Project")
    services['task_lifecycle_commands'].create_task(
        project.id, "Read Permission Task", start_date=date(2026, 5, 1), duration_days=2
    )
    services["resource_master_commands"].create_resource(
        "Read Permission Resource", hourly_rate=120.0
    )

    services["user_session"].clear()

    with pytest.raises(BusinessRuleError):
        services['project_query'].list_projects()
    with pytest.raises(BusinessRuleError):
        services['task_lookup_query'].list_tasks_for_project(project.id)
    with pytest.raises(BusinessRuleError):
        services["resource_query"].list_resources()
    with pytest.raises(BusinessRuleError):
        services["project_kpi_report"].get_project_kpis(project.id)
    with pytest.raises(BusinessRuleError):
        finance.get_finance_snapshot(project.id)
    with pytest.raises(BusinessRuleError):
        services["project_dashboard_query"].get_dashboard_data(project.id)
    with pytest.raises(BusinessRuleError, match="approval.request"):
        services["approval_queries"].list_requests(project_id=project.id)
    with pytest.raises(BusinessRuleError, match="audit.read"):
        audit.list_recent()


def test_viewer_cannot_manage_resources_costs_tasks_or_assignments(services):
    services["user_registration"].register_user(
        "viewer2", "StrongPass123", role_names=["viewer"]
    )
    target = services["user_registration"].register_user(
        "reset-target-viewer", "StrongPass123", role_names=["viewer"]
    )
    _login_as(services, "admin", "ChangeMe123!")

    services['cost_entry_query']
    services["project_resource_query"]

    project = services['project_create'].create_project("Permission project")
    resource = services["resource_master_commands"].create_resource(
        "Assigned Resource", hourly_rate=120.0
    )
    project_resource = services["project_resource_commands"].add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        planned_hours=40.0,
    )
    task = services['task_lifecycle_commands'].create_task(project_id=project.id, name="Permission task")
    assignment = services['task_assignment_commands'].assign_project_resource(task.id, project_resource.id, 50.0)

    _login_as(services, "viewer2", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services["password_commands"].reset_user_password(target.id, "ResetByViewer123")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services["resource_master_commands"].create_resource("Forbidden resource")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services['finance_governance_commands'].cost_entry(lambda handler: handler.create_manual_entry(
            project_id=project.id,
            command_id="viewer-forbidden-cost",
            description="Forbidden cost",
            amount=Decimal(100),
            currency_code="EUR",
            transaction_date=date(2026, 1, 1),
            cost_code_id="forbidden-cost-code",
        ))

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services['task_lifecycle_commands'].create_task(project_id=project.id, name="Forbidden task")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services['task_assignment_commands'].set_assignment_allocation(
            assignment.id, 40.0, expected_version=assignment.version
        )

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services["task_assignment_commands"].set_assignment_hours(assignment.id, 2.0)

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services['task_assignment_commands'].unassign_resource(assignment.id)


def test_viewer_cannot_manage_project_resources_or_calendar_or_leveling(services):
    services["user_registration"].register_user(
        "viewer3", "StrongPass123", role_names=["viewer"]
    )
    _login_as(services, "admin", "ChangeMe123!")

    services["project_resource_query"]
    ecs_commands = services["platform_calendar_commands"]

    project = services['project_create'].create_project("Ops permission project")
    resource = services["resource_master_commands"].create_resource(
        "Ops resource", hourly_rate=100.0
    )
    project_resource = services["project_resource_commands"].add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        planned_hours=16.0,
    )

    _login_as(services, "viewer3", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services["project_resource_commands"].add_to_project(
            project_id=project.id,
            resource_id=resource.id,
            planned_hours=8.0,
        )

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services["project_resource_commands"].update(
            pr_id=project_resource.id,
            hourly_rate=80.0,
            currency_code="EUR",
            planned_hours=20.0,
            is_active=True,
        )

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services["project_resource_commands"].set_active(project_resource.id, False)

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services["project_resource_commands"].delete(project_resource.id)

    with pytest.raises(BusinessRuleError, match="Permission denied"):
        ecs_commands.create_calendar(
            name="Viewer Calendar",
            code="VIEWER_CAL",
            calendar_type="standard",
        )


def test_governance_permissions_are_split_between_request_and_decide(
    services, monkeypatch
):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "project_cost.approve")
    services["user_registration"].register_user(
        "planner4", "StrongPass123", role_names=["planner"]
    )
    services["user_registration"].register_user(
        "viewer4", "StrongPass123", role_names=["viewer"]
    )
    _login_as(services, "admin", "ChangeMe123!")

    services['cost_entry_query']
    services['financial_configuration_query']
    approvals = services["approval_commands"]

    project = services['project_create'].create_project("Governance permission split")
    organization = services["tenant_context_service"].get_active_organization()
    cost_code = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(code="HOTEL", name="Hotel"))
    item = services['finance_governance_commands'].cost_entry(lambda handler: handler.create_manual_entry(
        project_id=project.id,
        command_id="governance-permission-split",
        description="Hotel",
        amount=Decimal(20),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 1, 1),
        cost_code_id=cost_code.id,
    ))
    item = services['finance_governance_commands'].cost_entry(lambda handler: handler.submit(item.id, expected_version=item.row_version))
    _login_as(services, "planner4", "StrongPass123")
    result = services['finance_governance_commands'].cost_entry_review(lambda handler: handler.approve(item.id, expected_version=item.row_version))
    assert result.outcome.value == "pending_approval"
    request_id = services["approval_queries"].list_pending(project_id=project.id)[0].id

    _login_as(services, "viewer4", "StrongPass123")
    with pytest.raises(BusinessRuleError, match="approval.request"):
        services['finance_governance_commands'].cost_entry_review(lambda handler: handler.approve(item.id, expected_version=item.row_version))
    with pytest.raises(BusinessRuleError, match="approval.decide"):
        approvals.approve_and_apply(request_id)


def test_timesheet_period_permissions_are_split_between_submit_approve_and_lock(
    services,
):
    services["user_registration"].register_user(
        "planner-timesheet", "StrongPass123", role_names=["planner"]
    )
    services["user_registration"].register_user(
        "viewer-timesheet", "StrongPass123", role_names=["viewer"]
    )
    _login_as(services, "admin", "ChangeMe123!")


    project = services['project_create'].create_project("Timesheet Permission Split")
    task = services['task_lifecycle_commands'].create_task(
        project.id,
        "Timesheet Permission Task",
        start_date=date(2026, 6, 1),
        duration_days=2,
    )
    resource = services["resource_master_commands"].create_resource(
        "Planner Logger", hourly_rate=100.0
    )
    assignment = services['task_assignment_commands'].assign_resource(task.id, resource.id, allocation_percent=100.0)
    services["time_entry_commands"].add_time_entry(
        assignment.id,
        entry_date=date(2026, 6, 2),
        hours=5.0,
        note="Initial work",
    )

    _login_as(services, "planner-timesheet", "StrongPass123")
    submitted = services["timesheet_period_transitions"].submit_timesheet_period(
        resource.id, period_start=date(2026, 6, 9)
    )
    assert submitted.status.value == "SUBMITTED"

    with pytest.raises(BusinessRuleError, match="timesheet.approve"):
        services["timesheet_period_transitions"].approve_timesheet_period(
            submitted.period_id,
            expected_version=submitted.version,
        )

    with pytest.raises(BusinessRuleError, match="timesheet.lock"):
        services["timesheet_period_transitions"].lock_timesheet_period(
            submitted.period_id,
            expected_version=submitted.version,
        )

    _login_as(services, "viewer-timesheet", "StrongPass123")
    with pytest.raises(BusinessRuleError, match="timesheet.submit"):
        services["timesheet_period_transitions"].submit_timesheet_period(
            resource.id, period_start=date(2026, 6, 1)
        )


def test_shared_time_permission_aliases_allow_time_queries_and_edits(services):
    user_session = services["user_session"]

    project = services['project_create'].create_project("Shared Time Permission Alias")
    task = services['task_lifecycle_commands'].create_task(
        project.id,
        "Alias Permission Task",
        start_date=date(2026, 7, 1),
        duration_days=2,
    )
    resource = services["resource_master_commands"].create_resource(
        "Alias Logger", hourly_rate=100.0
    )
    assignment = services['task_assignment_commands'].assign_resource(task.id, resource.id, allocation_percent=100.0)
    first = services["time_entry_commands"].add_time_entry(
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
    visible = services["time_entry_queries"].list_time_entries_for_assignment(
        assignment.id
    )
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
    second = services["time_entry_commands"].add_work_entry(
        assignment.id,
        entry_date=date(2026, 7, 2),
        hours=3.5,
        note="Shared manage permission entry",
    )
    assert second.work_allocation_id == assignment.id
    assert (
        len(
            services["time_entry_queries"].list_time_entries_for_work_allocation(
                assignment.id
            )
        )
        == 2
    )
