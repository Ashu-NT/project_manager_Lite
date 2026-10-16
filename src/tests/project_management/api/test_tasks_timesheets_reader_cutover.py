from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.tasks.api import (
    ProjectManagementTasksDesktopApi,
)
from src.core.modules.project_management.api.desktop.timesheets.api import (
    ProjectManagementTimesheetsDesktopApi,
)
from src.core.modules.project_management.application.scheduling.dto.responses.change_impact import (
    DownstreamExposureDto,
)
from src.core.modules.project_management.application.scheduling.dto.responses.overview import (
    TaskScheduleOverviewResponseDto,
)
from src.core.modules.project_management.contracts.reads.tasks import (
    TaskActivityPage,
    TaskAssignmentReadPage,
    TaskDependencyReadPage,
    TaskWorkspaceReadPage,
)
from src.core.modules.project_management.contracts.reads.tasks.models import (
    TaskTimeSummaryFact,
)
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetEntryReadPage,
    TimesheetHistoryReadPage,
    TimesheetResourceReadPage,
    TimesheetScope,
    TimesheetWorkspaceAccessFact,
)
from src.ui_qml.modules.project_management.presenters.tasks.schedule_impact_builder import (
    build_task_schedule_overview_state,
)
from src.ui_qml.modules.project_management.presenters.tasks.time_builder import (
    build_task_time_summary_dict,
)


@pytest.mark.parametrize(
    ("api_method", "query_method", "result"),
    [
        ("list_assignments_page", "query_task_assignments_page", TaskAssignmentReadPage()),
        ("list_dependencies_page", "query_task_dependencies_page", TaskDependencyReadPage()),
        ("list_task_activity_page", "query_task_activity_page", TaskActivityPage()),
    ],
)
def test_task_detail_pages_return_the_exact_reader_result(
    monkeypatch, api_method, query_method, result
):
    guard = Mock()
    monkeypatch.setattr(
        "src.core.modules.project_management.api.desktop.tasks.api.require_module_enabled",
        guard,
    )
    query = Mock()
    getattr(query, query_method).return_value = result
    api = ProjectManagementTasksDesktopApi(task_detail_query=query)

    assert getattr(api, api_method)("task-1", page=2, page_size=7) is result
    assert getattr(query, query_method).call_args.args == ("task-1",)
    assert getattr(query, query_method).call_args.kwargs["page"] == 2
    guard.assert_called_once()


def test_task_workspace_returns_reader_summary_and_sort_without_copying(monkeypatch):
    monkeypatch.setattr(
        "src.core.modules.project_management.api.desktop.tasks.api.require_module_enabled",
        Mock(),
    )
    result = TaskWorkspaceReadPage()
    query = Mock()
    query.query_workspace_page.return_value = result
    api = ProjectManagementTasksDesktopApi(task_workspace_query=query)

    assert api.list_task_page(project_id="project-1") is result
    assert query.query_workspace_page.call_args.kwargs["project_id"] == "project-1"


@pytest.mark.parametrize(
    ("api_method", "query_method", "result", "kwargs"),
    [
        (
            "get_timesheet_workspace_access", "get_timesheet_workspace_access",
            TimesheetWorkspaceAccessFact("actor", (TimesheetScope.MINE,), TimesheetScope.MINE), {},
        ),
        (
            "list_timesheet_resources_page", "query_timesheet_resources",
            TimesheetResourceReadPage(), {"scope": "team"},
        ),
        (
            "get_resource_timesheet_period", "get_timesheet_period", object(),
            {"scope": "mine", "resource_id": None, "period_start": date(2026, 10, 1)},
        ),
        (
            "list_resource_timesheet_entries_page", "query_timesheet_entries",
            TimesheetEntryReadPage(),
            {"scope": "all", "resource_id": "r", "period_start": date(2026, 10, 1)},
        ),
        (
            "list_resource_timesheet_history_page", "query_timesheet_history",
            TimesheetHistoryReadPage(), {"scope": "mine", "resource_id": None},
        ),
    ],
)
def test_timesheet_api_does_not_copy_or_format_scoped_reader_results(
    api_method, query_method, result, kwargs
):
    query = Mock()
    getattr(query, query_method).return_value = result
    api = ProjectManagementTimesheetsDesktopApi(timesheet_workspace_query=query)

    assert getattr(api, api_method)(**kwargs) is result
    for key, value in kwargs.items():
        assert getattr(query, query_method).call_args.kwargs[key] == value


def test_task_time_summary_keeps_decimal_zero_and_formats_only_in_presenter(monkeypatch):
    monkeypatch.setattr(
        "src.core.modules.project_management.api.desktop.tasks.api.require_module_enabled",
        Mock(),
    )
    fact = TaskTimeSummaryFact(
        "task-1", Decimal("0.00"), Decimal("1.25"), Decimal(0),
        Decimal("1.25"), "OVERRUN", 1,
    )
    query = Mock()
    query.get_task_time_summary.return_value = fact
    api = ProjectManagementTasksDesktopApi(task_assignment_commands=query)

    assert api.get_task_time_summary("task-1") is fact
    state = build_task_time_summary_dict(fact)
    assert state["plannedHoursLabel"] == "0.0 h"
    assert state["hasOverrun"] is True
    assert isinstance(fact.actual_hours, Decimal)


@pytest.mark.parametrize("total_float", [None, 0])
def test_schedule_overview_response_is_not_copied_and_presenter_keeps_none_vs_zero(total_float):
    result = TaskScheduleOverviewResponseDto(
        task_id="task-1", is_available=True, unavailable_reason="",
        current_start=date(2026, 10, 1), current_finish=None,
        is_critical=False, is_infeasible=False, total_float_days=total_float,
        free_float_days=0, baseline_finish=None, schedule_variance_days=0,
        drivers=(), dependency_conflicts=(), actual_variances=(),
        downstream=DownstreamExposureDto(0, 0, 0, 0),
    )
    query = Mock()
    query.get_task_schedule_overview.return_value = result
    api = ProjectManagementTasksDesktopApi(schedule_change_impact_query=query)

    assert api.get_task_schedule_overview("task-1", "project-1") is result
    state = build_task_schedule_overview_state(api, task_id="task-1", project_id="project-1")
    assert state["currentStartLabel"] == "2026-10-01"
    assert state["currentFinishLabel"] == "--"
    assert state["totalFloatDays"] == total_float
    assert state["scheduleVarianceDays"] == 0


def test_unavailable_schedule_overview_keeps_reason_in_presenter():
    api = ProjectManagementTasksDesktopApi()
    response = api.get_task_schedule_overview("task-1", "project-1")
    assert response.unavailable_reason == "service_not_configured"
    state = build_task_schedule_overview_state(
        SimpleNamespace(get_task_schedule_overview=lambda *_: response),
        task_id="task-1", project_id="project-1",
    )
    assert state["unavailableReason"] == "service_not_configured"
    assert state["isAvailable"] is False
