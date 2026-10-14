from datetime import date
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop import (
    build_project_management_timesheets_desktop_api,
)
from src.core.modules.project_management.domain.enums import (
    CostType,
    WorkerType,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.tests.project_management.api._timesheets_fakes_services import (
    _FakeProjectService,
    _FakeResourceService,
    _FakeTaskService,
)
from src.tests.project_management.api._timesheets_fakes_timesheet import (
    _FakeTimesheetService,
)


@pytest.mark.parametrize("operation", ("list_assignments", "list_resource_assignments", "build_assignment_snapshot"))
def test_timesheets_task_reads_check_module_before_handler(operation: str) -> None:
    catalog = SimpleNamespace(
        get_entitlement=lambda _code: SimpleNamespace(
            runtime_enabled=False,
            label="Project Management",
            lifecycle_status="inactive",
        )
    )
    failing_handler = SimpleNamespace(
        list_timesheet_assignment_contexts=lambda **_kwargs: pytest.fail("lookup called"),
        get_timesheet_assignment_context=lambda _id: pytest.fail("lookup called"),
        get_assignment=lambda _id: pytest.fail("assignment called"),
    )
    api = build_project_management_timesheets_desktop_api(
        task_lookup_query=failing_handler,
        task_assignment_commands=failing_handler,
        module_catalog_service=catalog,
    )

    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        if operation == "list_assignments":
            api.list_assignments(project_id="project-1")
        elif operation == "list_resource_assignments":
            api.list_resource_assignments(resource_id="resource-1")
        else:
            api.build_assignment_snapshot("assignment-1")


def test_project_management_timesheets_desktop_api_supports_assignment_periods_and_review() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    task_service = _FakeTaskService()
    task = task_service.create_task(
        project_id=project.id,
        name="Cable Pull",
        description="Primary feeder cable installation.",
        start_date=date(2026, 5, 3),
        duration_days=4,
    )
    resource_service = _FakeResourceService()
    resource = resource_service.create_resource(
        name="Electrical Crew",
        role="Lead Technician",
        hourly_rate=95.0,
        is_active=True,
        cost_type=CostType.LABOR,
        currency_code="eur",
        capacity_percent=110.0,
        address="Site Office",
        contact="crew@example.com",
        worker_type=WorkerType.EXTERNAL,
        employee_id=None,
    )
    assignment = task_service.create_assignment(
        task_id=task.id,
        resource_id=resource.id,
        allocation_percent=100.0,
    )
    timesheet_service = _FakeTimesheetService(
        task_service=task_service,
        resource_service=resource_service,
    )
    task_service._project_service = project_service
    task_service._resource_service = resource_service
    api = build_project_management_timesheets_desktop_api(
        project_service=project_service,
        task_lookup_query=task_service,
        task_assignment_commands=task_service,
        resource_query=resource_service,
        # The fake implements every Time capability the adapter uses.
        timesheet_review_query=timesheet_service,
        time_entry_commands=timesheet_service,
        time_entry_queries=timesheet_service,
        timesheet_period_query=timesheet_service,
        timesheet_period_transitions=timesheet_service,
    )

    assert api.list_projects()[0].label == "Plant Upgrade"
    assert api.list_queue_statuses()[1].value == "OPEN"
    assert api.list_assignments(project_id=project.id)[0].label == (
        "Plant Upgrade | Cable Pull | Electrical Crew"
    )

    created_entry = api.add_time_entry(
        SimpleNamespace(
            assignment_id=assignment.id,
            entry_date=date(2026, 5, 3),
            hours=8.0,
            note="Cable tray installation",
        )
    )
    api.add_time_entry(
        SimpleNamespace(
            assignment_id=assignment.id,
            entry_date=date(2026, 5, 4),
            hours=6.5,
            note="Termination prep",
        )
    )
    updated_entry = api.update_time_entry(
        SimpleNamespace(
            entry_id=created_entry.entry_id,
            expected_version=created_entry.version,
            entry_date=date(2026, 5, 3),
            hours=7.5,
            note="Cable tray installation revised",
        )
    )
    snapshot = api.build_assignment_snapshot(assignment.id)
    timesheet_service.resource_period_read_count = 0
    submitted_period = api.submit_period(
        resource_id=resource.id,
        period_start=date(2026, 5, 1),
        note="Submitted for supervisor review.",
    )
    assert timesheet_service.resource_period_read_count == 1
    review_queue = api.list_review_queue_page().items
    review_detail = api.get_review_detail(submitted_period.period_id)
    approved_period = api.approve_period(
        submitted_period.period_id,
        expected_version=submitted_period.version,
        note="Approved after weekly close review.",
    )
    locked_period = api.lock_period(
        approved_period.period_id,
        expected_version=approved_period.version,
        note="Month-end payroll lock.",
    )
    unlocked_period = api.unlock_period(
        locked_period.period_id,
        expected_version=locked_period.version,
        note="Reopened for correction.",
    )
    api.delete_time_entry(
        created_entry.entry_id,
        expected_version=updated_entry.version,
    )

    assert updated_entry.hours_label == "7.50h"
    assert snapshot.assignment.resource_name == "Electrical Crew"
    assert snapshot.entries[0].entry_id == created_entry.entry_id
    assert snapshot.resource_period_total_hours_label == "14.00h"
    assert submitted_period.status == "SUBMITTED"
    assert review_queue[0].entry_count == 2
    assert review_detail.summary.resource_name == "Electrical Crew"
    assert review_detail.summary.project_count == 1
    assert approved_period.status == "APPROVED"
    assert locked_period.status == "LOCKED"
    assert unlocked_period.status == "APPROVED"
    assert unlocked_period.version == submitted_period.version + 3
    assert [entry.entry_id for entry in api.build_assignment_snapshot(assignment.id).entries] != [
        created_entry.entry_id
    ]
