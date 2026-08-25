from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from src.core.modules.project_management.contracts.reads.timesheets import TimesheetScope
from src.core.modules.project_management.domain.enums import ResourceKind, WorkerType
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
)
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


def _build_owner_timesheet(services):
    principal = services["user_session"].principal
    employee = services["employee_service"].create_employee(
        employee_code="R5F1-OWNER",
        full_name="Timesheet Owner",
        user_id=principal.user_id,
    )
    resource = services["resource_service"].create_resource(
        name="Timesheet Owner",
        role="Engineer",
        worker_type=WorkerType.EMPLOYEE,
        employee_id=employee.id,
    )
    project = services["project_service"].create_project("R5F1 Delivery")
    task = services["task_service"].create_task(
        project.id,
        "Owner Workflow",
        start_date=date(2026, 8, 1),
        duration_days=20,
    )
    assignment = services["task_service"].assign_resource(task.id, resource.id)
    return employee, resource, project, task, assignment


def test_owner_timesheet_read_is_scoped_paged_sorted_and_backend_aggregated(services) -> None:
    _, resource, project, task, assignment = _build_owner_timesheet(services)
    timesheets = services["timesheet_service"]
    for work_date, hours in (
        (date(2026, 8, 3), 7.5),
        (date(2026, 8, 4), 2.0),
        (date(2026, 8, 5), 5.0),
    ):
        timesheets.add_time_entry(
            assignment.id,
            entry_date=work_date,
            hours=hours,
            note=f"Work on {work_date.isoformat()}",
        )

    period = timesheets.get_owner_timesheet_period(period_start=date(2026, 8, 18))
    first = timesheets.query_owner_time_entries(
        period_start=date(2026, 8, 1),
        page=1,
        page_size=2,
        sort_key="hours",
        sort_direction="asc",
    )
    second = timesheets.query_owner_time_entries(
        period_start=date(2026, 8, 1),
        page=2,
        page_size=2,
        sort_key="hours",
        sort_direction="asc",
    )

    assert period.resource_id == resource.id
    assert period.status is TimesheetPeriodStatus.OPEN
    assert period.total_hours == 14.5
    assert period.entry_count == 3
    assert period.project_count == 1
    assert period.task_count == 1
    assert period.can_submit is True
    assert first.total == 3
    assert [float(row.hours) for row in first.items] == [2.0, 5.0]
    assert [float(row.hours) for row in second.items] == [7.5]
    assert all(row.project_id == project.id for row in (*first.items, *second.items))
    assert all(row.task_id == task.id for row in (*first.items, *second.items))


def test_owner_mutations_deny_another_resource_and_enforce_selected_period(services) -> None:
    _, _, _, _, owner_assignment = _build_owner_timesheet(services)
    other = services["resource_service"].create_resource(
        name="Another Resource",
        role="Engineer",
    )
    project = services["project_service"].create_project("Other Work")
    task = services["task_service"].create_task(project.id, "Other Task")
    other_assignment = services["task_service"].assign_resource(task.id, other.id)
    timesheets = services["timesheet_service"]

    with pytest.raises(BusinessRuleError, match="owner"):
        timesheets.add_owner_time_entry(
            other_assignment.id,
            period_start=date(2026, 8, 1),
            entry_date=date(2026, 8, 5),
            hours=4,
        )

    with pytest.raises(Exception, match="selected reporting period"):
        timesheets.add_owner_time_entry(
            owner_assignment.id,
            period_start=date(2026, 8, 1),
            entry_date=date(2026, 9, 1),
            hours=4,
        )


def test_owner_submit_is_versioned_and_populates_review_queue(services) -> None:
    _, _, _, _, assignment = _build_owner_timesheet(services)
    timesheets = services["timesheet_service"]
    timesheets.add_time_entry(
        assignment.id,
        entry_date=date(2026, 8, 4),
        hours=8,
        note="Ready for review",
    )
    before = timesheets.get_owner_timesheet_period(period_start=date(2026, 8, 1))

    submitted = timesheets.submit_owner_timesheet_period(
        period_start=date(2026, 8, 1),
        expected_version=before.version,
        note="Owner submission",
    )
    after = timesheets.get_owner_timesheet_period(period_start=date(2026, 8, 1))
    queue = timesheets.query_review_queue_page(
        status=TimesheetPeriodStatus.SUBMITTED
    )
    history = timesheets.query_owner_timesheet_history(page=1, page_size=12)

    assert submitted.status is TimesheetPeriodStatus.SUBMITTED
    assert after.status is TimesheetPeriodStatus.SUBMITTED
    assert after.version == before.version + 1
    assert after.can_add_entry is False
    assert after.can_submit is False
    assert queue.total == 1
    assert queue.items[0].period_id == after.period_id
    assert history.total == 1
    assert history.items[0].period_id == after.period_id

    with pytest.raises(ConcurrencyError):
        timesheets.submit_owner_timesheet_period(
            period_start=date(2026, 8, 1),
            expected_version=before.version,
        )


def test_r5f1_navigation_keeps_timesheets_and_review_queue_distinct() -> None:
    from src.ui_qml.modules.project_management.controllers.common.pm_workspace_navigation_controller import (
        PMWorkspaceNavigationController,
    )

    items = PMWorkspaceNavigationController().navigationItems
    by_id = {item["id"]: item for item in items}

    assert by_id["timesheets"]["group"] == "Work"
    assert by_id["timesheets"]["label"] == "Timesheets"
    assert by_id["review_queue"]["group"] == "Workload Management"
    assert {
        item["label"]
        for item in items
        if item["group"] == "Workload Management"
    } == {"Resources", "Review Queue"}


def test_resource_timesheet_scopes_enforce_target_and_eligibility(services) -> None:
    _, owner, _, _, _ = _build_owner_timesheet(services)
    external = services["resource_service"].create_resource(
        name="External Without Login",
        role="Consultant",
        kind=ResourceKind.PERSON,
        worker_type=WorkerType.EXTERNAL,
    )
    crew = services["resource_service"].create_resource(
        name="Field Crew",
        role="Crew",
        kind=ResourceKind.CREW,
        worker_type=WorkerType.EXTERNAL,
    )
    timesheets = services["timesheet_service"]

    access = timesheets.get_timesheet_workspace_access()
    all_page = timesheets.query_timesheet_resources(
        scope=TimesheetScope.ALL, page=1, page_size=20
    )

    assert access.available_scopes == (
        TimesheetScope.MINE,
        TimesheetScope.TEAM,
        TimesheetScope.ALL,
    )
    assert access.mine_resource.resource_id == owner.id
    assert external.id in {item.resource_id for item in all_page.items}
    assert crew.id not in {item.resource_id for item in all_page.items}

    original = services["user_session"].principal
    services["user_session"].set_principal(
        replace(
            original,
            role_names=frozenset({"team_member"}),
            permissions=frozenset(
                {"timesheet.read_own", "timesheet.edit_own", "timesheet.submit"}
            ),
            scoped_access={},
            project_access={},
        )
    )
    with pytest.raises(Exception, match="not available"):
        timesheets.get_timesheet_period(
            scope=TimesheetScope.MINE,
            resource_id=external.id,
            period_start=date(2026, 8, 1),
        )
    with pytest.raises(BusinessRuleError, match="Permission denied"):
        timesheets.query_timesheet_resources(scope=TimesheetScope.ALL)


def test_reviewer_permission_does_not_grant_timesheet_edit_other(services) -> None:
    _, _, _, _, assignment = _build_owner_timesheet(services)
    original = services["user_session"].principal
    services["user_session"].set_principal(
        replace(
            original,
            role_names=frozenset({"reviewer"}),
            permissions=frozenset({"timesheet.approve"}),
            scoped_access={},
            project_access={},
        )
    )
    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services["timesheet_service"].add_timesheet_entry(
            assignment.id,
            scope=TimesheetScope.ALL,
            resource_id=assignment.resource_id,
            period_start=date(2026, 8, 1),
            entry_date=date(2026, 8, 4),
            hours=4,
        )


def test_external_without_login_supports_governed_delegated_lifecycle(services) -> None:
    external = services["resource_service"].create_resource(
        name="Delegated Contractor",
        role="Consultant",
        kind=ResourceKind.PERSON,
        worker_type=WorkerType.EXTERNAL,
    )
    project = services["project_service"].create_project("Delegated Delivery")
    task = services["task_service"].create_task(project.id, "Consulting")
    assignment = services["task_service"].assign_resource(task.id, external.id)
    timesheets = services["timesheet_service"]

    entry = timesheets.add_timesheet_entry(
        assignment.id,
        scope=TimesheetScope.ALL,
        resource_id=external.id,
        period_start=date(2026, 8, 1),
        entry_date=date(2026, 8, 7),
        hours=6,
        note="Entered by timekeeper",
    )
    before = timesheets.get_timesheet_period(
        scope=TimesheetScope.ALL,
        resource_id=external.id,
        period_start=date(2026, 8, 1),
    )
    submitted = timesheets.submit_resource_timesheet_period(
        scope=TimesheetScope.ALL,
        resource_id=external.id,
        period_start=date(2026, 8, 1),
        expected_version=before.version,
        note="Submitted on behalf",
    )

    assert entry.author_user_id == services["user_session"].principal.user_id
    assert submitted.resource_id == external.id
    assert submitted.submitted_by_user_id == services["user_session"].principal.user_id
    assert submitted.status is TimesheetPeriodStatus.SUBMITTED


def test_team_selector_uses_explicit_project_scope(services) -> None:
    in_team = services["resource_service"].create_resource(
        name="In Team", role="Engineer", kind=ResourceKind.PERSON
    )
    out_team = services["resource_service"].create_resource(
        name="Out Team", role="Engineer", kind=ResourceKind.PERSON
    )
    team_project = services["project_service"].create_project("Team Project")
    other_project = services["project_service"].create_project("Other Project")
    team_task = services["task_service"].create_task(team_project.id, "Team Task")
    other_task = services["task_service"].create_task(other_project.id, "Other Task")
    services["task_service"].assign_resource(team_task.id, in_team.id)
    services["task_service"].assign_resource(other_task.id, out_team.id)
    original = services["user_session"].principal
    scoped = {"project": {team_project.id: frozenset({"timesheet.read_team"})}}
    services["user_session"].set_principal(
        replace(
            original,
            role_names=frozenset({"project_timekeeper"}),
            permissions=frozenset({"timesheet.read_team"}),
            scoped_access=scoped,
            project_access=scoped["project"],
        )
    )

    page = services["timesheet_service"].query_timesheet_resources(
        scope=TimesheetScope.TEAM
    )

    assert {item.resource_id for item in page.items} == {in_team.id}
    with pytest.raises(Exception, match="not available"):
        services["timesheet_service"].get_timesheet_period(
            scope=TimesheetScope.TEAM,
            resource_id=out_team.id,
            period_start=date(2026, 8, 1),
        )
