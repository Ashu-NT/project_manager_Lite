from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.domain.enums import WorkerType
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
)
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus
from src.ui_qml.modules.project_management.presenters.owner_timesheets import (
    OwnerTimesheetsPresenter,
)


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


def test_owner_presenter_returns_setup_state_when_principal_has_no_resource() -> None:
    class MissingOwnerApi:
        def get_owner_period(self, *, period_start):
            raise NotFoundError(
                "No active project resource is linked to the signed-in user.",
                code="TIMESHEET_OWNER_RESOURCE_NOT_FOUND",
            )

    state = OwnerTimesheetsPresenter(desktop_api=MissingOwnerApi()).build_state(
        period_start=date(2026, 8, 1),
        search_text="",
        project_id="all",
        task_id="all",
        page=1,
        page_size=25,
        sort_key="date",
        sort_direction="desc",
        history_page=1,
        history_page_size=12,
    )

    assert state["period"]["ownerAvailable"] is False
    assert state["period"]["canAddEntry"] is False
    assert state["period"]["canSubmit"] is False
    assert state["entries"] == []
    assert state["history"] == []
    assert "administrator" in state["period"]["setupMessage"]
