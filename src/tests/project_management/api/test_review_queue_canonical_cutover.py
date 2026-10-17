from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.timesheets.api import (
    ProjectManagementTimesheetsDesktopApi,
)
from src.core.modules.project_management.application.timesheets.dto.commands.time_entries import (
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
)
from src.core.modules.project_management.application.timesheets.mappers.time_entries import (
    map_timesheet_entry,
)
from src.core.modules.project_management.contracts.reads.timesheets.review_reader import (
    TimesheetReviewInspectorFact,
    TimesheetReviewQueueFact,
    TimesheetReviewReadPage,
)
from src.core.platform.domain.time_management.time import (
    TimeEntry,
    TimesheetPeriodStatus,
)
from src.ui_qml.modules.project_management.presenters.review_queue.formatting import (
    format_hours,
)
from src.ui_qml.modules.project_management.presenters.review_queue.review_mapper import (
    to_review_queue_record,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, "-"), (Decimal("0"), "0.00h"), (Decimal("9007199254740993.25"), "9007199254740993.25h")],
)
def test_review_queue_hours_formatting_preserves_missing_zero_and_decimal(value, expected):
    assert format_hours(value) == expected


def test_review_queue_preserves_reader_result_identity_without_project_reload():
    row = TimesheetReviewQueueFact(
        item_id="period",
        timesheet_period_id="period",
        version=7,
        resource_id="resource",
        resource_name="Person",
        resource_code="RES-1",
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
        status=TimesheetPeriodStatus.SUBMITTED,
        submitted_at=None,
        submitted_by_username=None,
        decided_at=None,
        decided_by_username=None,
        decision_note=None,
        total_hours=0.0,
        project_count=1,
        task_count=0,
        entry_count=0,
        generic_entry_count=0,
        project_ids=("project",),
        can_approve=False,
        can_reject=True,
    )
    page = TimesheetReviewReadPage(items=(row,), total=200, page=2)
    detail = TimesheetReviewInspectorFact(summary=row)
    query = Mock()
    query.query_review_queue_page.return_value = page
    query.get_review_queue_inspector.return_value = detail
    projects = Mock()
    api = ProjectManagementTimesheetsDesktopApi(
        timesheet_review_query=query,
        project_service=projects,
    )
    assert api.list_review_queue_page(page=2) is page
    assert api.get_review_detail("period") is detail
    assert projects.mock_calls == []

    view = to_review_queue_record(row, project_labels={"project": "Project"})
    assert view.subtitle == "Project"
    assert view.supporting_text == "0.00h across 0 entry or entries."
    assert view.state["version"] == 7
    assert view.state["status"] == "SUBMITTED"
    assert view.can_primary_action is False
    assert view.can_secondary_action is True


@pytest.mark.parametrize("scoped", [False, True])
@pytest.mark.parametrize("updating", [False, True])
def test_time_entry_commands_pass_original_command_and_detached_result(
    scoped, updating
):
    source = TimeEntry.create(
        "allocation", assignment_id="assignment", entry_date=date(2026, 5, 4), hours=2.5
    )
    response = map_timesheet_entry(source)
    command = (
        TimesheetEntryUpdateCommand(response.entry_id, response.version, hours=3)
        if updating
        else TimesheetEntryCreateCommand("assignment", date(2026, 5, 4), 2.5)
    )
    commands = Mock()
    handler_method = (
        commands.update_timesheet_entry if updating else commands.add_timesheet_entry
    )
    handler_method.return_value = response
    api = ProjectManagementTimesheetsDesktopApi(timesheet_workspace_commands=commands)
    suffix = "resource_time_entry" if scoped else "time_entry"
    method = getattr(api, ("update_" if updating else "add_") + suffix)
    context = (
        dict(scope="all", resource_id="resource", period_start=date(2026, 5, 1))
        if scoped
        else {}
    )
    assert method(command, **context) is response
    handler_method.assert_called_once_with(command, **context)
    source.hours = 8
    assert response.hours == Decimal("2.5")
    assert not hasattr(response, "hours_label")
