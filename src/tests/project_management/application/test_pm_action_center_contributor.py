from __future__ import annotations

from datetime import date

from src.core.application.global_overview.contracts.action_center import ActionCenterContext
from src.core.modules.project_management.application.global_overview.pm_action_center_contributor import (
    ProjectManagementActionCenterContributor,
)
from src.core.modules.project_management.domain.enums import TaskStatus, WorkerType
from src.core.modules.project_management.domain.scheduling.baseline import BaselineStatus
from src.core.shared.resource_identity.contracts import ResourceIdentityReader


class _NullResourceIdentityReader:
    """Used for the timesheets-only test where no employee/user link is
    needed for Task resolution."""

    def resolve_resource_for_user(self, *, user_id, tenant_id, organization_id):
        return None


def _contributor(services, resource_identity_reader: ResourceIdentityReader):
    from src.core.modules.project_management.infrastructure.persistence.reads.timesheets.sqlalchemy_workspace_reader import (
        SqlAlchemyTimesheetWorkspaceReader,
    )

    return ProjectManagementActionCenterContributor(
        task_service=services["task_service"],
        baseline_service=services["baseline_service"],
        project_service=services["project_service"],
        resource_identity_reader=resource_identity_reader,
        timesheet_workspace_reader=SqlAlchemyTimesheetWorkspaceReader(
            session=services["session"], resource_identity_reader=resource_identity_reader
        ),
    )


def _context(services) -> ActionCenterContext:
    principal = services["user_session"].principal
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    organization = services["tenant_context_service"].get_active_organization()
    return ActionCenterContext(
        user_id=principal.user_id, tenant_id=tenant_id, organization_id=organization.id
    )


def _resource_identity_reader(services):
    from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
        SqlAlchemyResourceIdentityReader,
    )

    return SqlAlchemyResourceIdentityReader(session=services["session"])


def _setup_user_employee_resource(services, *, suffix: str):
    organization = services["tenant_context_service"].get_active_organization()
    user = services["auth_service"].register_user(
        f"pm-action-center-{suffix}", "StrongPass123", role_names=["viewer"]
    )
    employee = services["employee_service"].create_employee(
        employee_code=f"EMP-AC-{suffix}",
        full_name=f"Action Center {suffix}",
        user_id=user.id,
    )
    resource = services["resource_service"].create_resource(
        f"Action Center Resource {suffix}",
        worker_type=WorkerType.EMPLOYEE,
        employee_id=employee.id,
    )
    return organization, user, resource


# -- A. Tasks -----------------------------------------------------------------


def test_tasks_resolve_through_resource_identity_and_include_only_open_states(services):
    organization, user, resource = _setup_user_employee_resource(services, suffix="tasks")
    project = services["project_service"].create_project(
        "Action Center Tasks Project", financial_currency_code=organization.base_currency
    )
    other_resource = services["resource_service"].create_resource("Unrelated Resource")

    todo = services["task_service"].create_task(
        project.id, "Todo task", start_date=date(2026, 6, 1), duration_days=2, deadline=date(2026, 9, 20)
    )
    in_progress = services["task_service"].create_task(
        project.id,
        "In progress task",
        start_date=date(2026, 6, 3),
        duration_days=2,
        status=TaskStatus.IN_PROGRESS,
    )
    blocked = services["task_service"].create_task(
        project.id, "Blocked task", start_date=date(2026, 6, 5), duration_days=2,
    )
    services["task_service"].set_status(blocked.id, TaskStatus.BLOCKED)
    done = services["task_service"].create_task(
        project.id, "Done task", start_date=date(2026, 6, 7), duration_days=2,
    )
    services["task_service"].set_status(done.id, TaskStatus.DONE)

    services["task_service"].assign_resource(todo.id, resource.id, allocation_percent=50.0)
    services["task_service"].assign_resource(in_progress.id, resource.id, allocation_percent=50.0)
    services["task_service"].assign_resource(blocked.id, resource.id, allocation_percent=50.0)
    services["task_service"].assign_resource(done.id, resource.id, allocation_percent=50.0)
    unrelated_task = services["task_service"].create_task(
        project.id, "Unrelated task", start_date=date(2026, 6, 9), duration_days=2,
    )
    services["task_service"].assign_resource(unrelated_task.id, other_resource.id, allocation_percent=50.0)

    reader = _resource_identity_reader(services)
    contributor = _contributor(services, reader)
    context = ActionCenterContext(user_id=user.id, tenant_id=services["tenant_context_service"].get_active_tenant_id(), organization_id=organization.id)

    contribution = contributor.collect(context, preview_limit=10)

    assigned_task_ids = {item.subject_id for item in contribution.items if item.kind == "pm_task"}
    assert assigned_task_ids == {todo.id, in_progress.id, blocked.id}
    assert done.id not in assigned_task_ids
    assert unrelated_task.id not in assigned_task_ids
    assert contribution.summary.assigned_work == 3

    todo_item = next(item for item in contribution.items if item.subject_id == todo.id)
    assert todo_item.due_at == date(2026, 9, 20)
    assert todo_item.route_id == "project_management.tasks"


# -- B. Baselines --------------------------------------------------------------


def test_baselines_include_only_submitted_across_accessible_projects_regardless_of_status(
    services,
):
    organization, user, resource = _setup_user_employee_resource(services, suffix="baselines")
    active_project = services["project_service"].create_project(
        "Active Baseline Project", financial_currency_code=organization.base_currency
    )
    on_hold_project = services["project_service"].create_project(
        "On Hold Baseline Project", financial_currency_code=organization.base_currency
    )
    services["task_service"].create_task(
        active_project.id, "Seed task A", start_date=date(2026, 6, 1), duration_days=2
    )
    services["task_service"].create_task(
        on_hold_project.id, "Seed task B", start_date=date(2026, 6, 1), duration_days=2
    )

    submitted_baseline = services["baseline_service"].create_baseline(
        active_project.id, "Baseline A", rate_as_of=date(2026, 6, 1)
    )
    services["baseline_service"].submit_baseline(submitted_baseline.id, submitted_by="admin")

    draft_baseline = services["baseline_service"].create_baseline(
        active_project.id, "Baseline B (draft)", rate_as_of=date(2026, 6, 1)
    )
    assert draft_baseline.status == BaselineStatus.DRAFT

    submitted_on_other_project = services["baseline_service"].create_baseline(
        on_hold_project.id, "Baseline C", rate_as_of=date(2026, 6, 1)
    )
    services["baseline_service"].submit_baseline(submitted_on_other_project.id, submitted_by="admin")

    reader = _resource_identity_reader(services)
    contributor = _contributor(services, reader)
    context = ActionCenterContext(
        user_id=user.id,
        tenant_id=services["tenant_context_service"].get_active_tenant_id(),
        organization_id=organization.id,
    )

    contribution = contributor.collect(context, preview_limit=10)

    baseline_ids = {item.subject_id for item in contribution.items if item.kind == "baseline_review"}
    assert baseline_ids == {submitted_baseline.id, submitted_on_other_project.id}
    assert draft_baseline.id not in baseline_ids
    assert contribution.summary.reviews_and_approvals == 2
    assert all(
        item.due_at is None for item in contribution.items if item.kind == "baseline_review"
    )


# -- C. Timesheets ---------------------------------------------------------------


def test_timesheets_include_open_and_rejected_but_not_approved_or_locked(services):
    organization, user, resource = _setup_user_employee_resource(services, suffix="timesheets")
    project = services["project_service"].create_project(
        "Action Center Timesheet Project", financial_currency_code=organization.base_currency
    )
    task = services["task_service"].create_task(
        project.id, "Timesheet task", start_date=date(2026, 6, 1), duration_days=10
    )
    assignment = services["task_service"].assign_resource(task.id, resource.id, allocation_percent=100.0)

    # OPEN period: entries logged, never submitted.
    services["task_service"].add_time_entry(assignment.id, entry_date=date(2026, 6, 4), hours=4)

    # REJECTED period: a different period, submitted then rejected.
    services["task_service"].add_time_entry(assignment.id, entry_date=date(2026, 7, 4), hours=4)
    submitted = services["timesheet_service"].submit_timesheet_period(
        resource.id, period_start=date(2026, 7, 1)
    )
    services["timesheet_service"].reject_timesheet_period(
        submitted.period_id, expected_version=submitted.version, note="Please recheck hours"
    )

    # APPROVED period: submitted then approved -- must be excluded.
    services["task_service"].add_time_entry(assignment.id, entry_date=date(2026, 8, 4), hours=4)
    approved_submission = services["timesheet_service"].submit_timesheet_period(
        resource.id, period_start=date(2026, 8, 1)
    )
    services["timesheet_service"].approve_timesheet_period(
        approved_submission.period_id, expected_version=approved_submission.version, note="OK"
    )

    reader = _resource_identity_reader(services)
    contributor = _contributor(services, reader)
    context = ActionCenterContext(
        user_id=user.id,
        tenant_id=services["tenant_context_service"].get_active_tenant_id(),
        organization_id=organization.id,
    )

    contribution = contributor.collect(context, preview_limit=10)

    timesheet_items = [item for item in contribution.items if item.kind == "timesheet"]
    action_states = {item.action_state for item in timesheet_items}
    assert action_states == {"open", "rejected"}
    assert contribution.summary.submissions == 2
    assert all(item.due_at is None for item in timesheet_items)

    open_item = next(item for item in timesheet_items if item.action_state == "open")
    assert open_item.title == "Submit timesheet"
    rejected_item = next(item for item in timesheet_items if item.action_state == "rejected")
    assert rejected_item.title == "Correct and resubmit timesheet"


def test_all_action_items_equals_the_sum_of_the_three_pm_categories(services):
    organization, user, resource = _setup_user_employee_resource(services, suffix="parity")
    project = services["project_service"].create_project(
        "Action Center Parity Project", financial_currency_code=organization.base_currency
    )
    task = services["task_service"].create_task(
        project.id, "Parity task", start_date=date(2026, 6, 1), duration_days=2
    )
    services["task_service"].assign_resource(task.id, resource.id, allocation_percent=50.0)

    baseline = services["baseline_service"].create_baseline(
        project.id, "Parity Baseline", rate_as_of=date(2026, 6, 1)
    )
    services["baseline_service"].submit_baseline(baseline.id, submitted_by="admin")

    assignment = services["task_service"].assign_resource(
        services["task_service"].create_task(
            project.id, "Timesheet task", start_date=date(2026, 6, 1), duration_days=2
        ).id,
        resource.id,
        allocation_percent=50.0,
    )
    services["task_service"].add_time_entry(assignment.id, entry_date=date(2026, 6, 4), hours=2)

    reader = _resource_identity_reader(services)
    contributor = _contributor(services, reader)
    context = ActionCenterContext(
        user_id=user.id,
        tenant_id=services["tenant_context_service"].get_active_tenant_id(),
        organization_id=organization.id,
    )

    summary = contributor.collect(context, preview_limit=50).summary

    assert summary.all_action_items == (
        summary.reviews_and_approvals + summary.assigned_work + summary.submissions
    )
    # 2 open tasks (the parity task + the task created for the timesheet
    # assignment, both default TODO), 1 submitted baseline, 1 open timesheet.
    assert (summary.assigned_work, summary.reviews_and_approvals, summary.submissions) == (2, 1, 1)
    assert summary.all_action_items == 4
