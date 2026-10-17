from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.modules.project_management.application.scheduling.baselines.queries.catalog import (
    BaselineQueryHandler,
)
from src.core.modules.project_management.application.scheduling.dto.commands.baselines import (
    SchedulingBaselineCreateCommand,
)
from src.core.modules.project_management.application.scheduling.mappers.baselines import (
    map_baseline,
    map_baseline_comparison,
    map_baseline_variance,
)
from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineVarianceRecord,
    ProjectBaseline,
)
from src.core.platform.api.desktop.time_management.calendar.models.platform_calendar import (
    CalendarDto,
)
from src.core.platform.application.time_management.calendar.dto.responses.working_calendar import (
    WorkingCalendarHolidayDto,
)


def test_baseline_catalog_is_mapped_once_and_api_reuses_query_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = ProjectBaseline(
        id="base-1",
        project_id="project-1",
        name="Original",
        created_at=date(2026, 5, 1),
    )
    repo = Mock()
    repo.list_for_project.return_value = [baseline]
    query = BaselineQueryHandler(baseline_repo=repo)
    permission = Mock()
    project_permission = Mock()
    monkeypatch.setattr(
        "src.core.modules.project_management.application.scheduling.baselines.queries.catalog.require_permission",
        permission,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.scheduling.baselines.queries.catalog.require_project_permission",
        project_permission,
    )
    rows = query.query_baseline_responses("project-1")
    permission.assert_called_once_with(
        None, "project.read", operation_label="list baselines"
    )
    project_permission.assert_called_once_with(
        None, "project-1", "project.read", operation_label="list baselines"
    )
    repo.list_for_project.assert_called_once_with("project-1")
    canonical_query = Mock()
    canonical_query.query_baseline_responses.return_value = rows
    api = ProjectManagementSchedulingDesktopApi(baseline_query=canonical_query)

    assert api.list_baselines(" project-1 ") is rows
    canonical_query.query_baseline_responses.assert_called_once_with("project-1")
    assert api.list_baselines(" ") == ()
    assert ProjectManagementSchedulingDesktopApi().list_baselines("project-1") == ()
    baseline.name = "Later mutation"
    assert rows[0].name == "Original"
    assert rows[0].can_submit
    assert not hasattr(rows[0], "status_label")
    assert not hasattr(rows[0], "created_at_label")
    with pytest.raises(FrozenInstanceError):
        setattr(rows[0], "name", "Changed")


def test_baseline_creation_snapshots_domain_result_without_an_extra_query() -> None:
    baseline = ProjectBaseline(
        id="base-1",
        project_id="project-1",
        name="Original",
        created_at=date(2026, 5, 1),
    )
    commands = Mock()
    commands.create_baseline.return_value = baseline
    query = Mock()
    api = ProjectManagementSchedulingDesktopApi(
        baseline_commands=commands, baseline_query=query
    )
    command = SchedulingBaselineCreateCommand(project_id="project-1", name="Original")

    response = api.create_baseline(command)

    commands.create_baseline.assert_called_once_with(command)
    query.assert_not_called()
    assert query.mock_calls == []
    assert response == map_baseline(baseline)
    baseline.submit("Planner")
    assert response.status == "draft"
    assert response.submitted_by is None


def test_baseline_read_errors_are_not_hidden_and_variance_result_is_reused() -> None:
    query = Mock()
    api = ProjectManagementSchedulingDesktopApi(baseline_query=query)
    query.query_baseline_responses.side_effect = PermissionError("Denied")
    with pytest.raises(PermissionError, match="Denied"):
        api.list_baselines("project-1")
    rows = (object(),)
    query.query_variance_responses.return_value = rows
    assert api.list_baseline_variance_records(" base-1 ") is rows
    query.query_variance_responses.assert_called_once_with("base-1")


def test_baseline_monetary_results_preserve_decimal_precision() -> None:
    amount = Decimal("12345678901234567890.123456789")
    comparison = map_baseline_comparison(
        SimpleNamespace(
            task_id="task-1",
            task_name="Task",
            change_type="CHANGED",
            baseline_a_start=None,
            baseline_a_finish=None,
            baseline_b_start=None,
            baseline_b_finish=None,
            start_shift_days=0,
            finish_shift_days=0,
            duration_delta_days=0,
            planned_cost_delta=amount,
        )
    )
    record = BaselineVarianceRecord(
        id="variance-1",
        project_id="project-1",
        new_baseline_id="base-2",
        superseded_baseline_id="base-1",
        task_id="task-1",
        task_name="Task",
        start_variance_days=0,
        finish_variance_days=0,
        cost_variance=amount,
        created_at=date(2026, 5, 1),
    )
    assert comparison.planned_cost_delta is amount
    assert map_baseline_variance(record).cost_variance == amount


def test_platform_calendar_options_reuse_canonical_results_and_snapshot_preserves_policy() -> (
    None
):
    calendar = CalendarDto(
        "cal-1", "org-1", "STD", "Standard", "work", "Europe/Berlin", True, True
    )
    calendars = (calendar,)
    platform = Mock()
    platform.list_calendars.return_value = SimpleNamespace(ok=True, data=calendars)
    platform.get_default_calendar.return_value = SimpleNamespace(ok=True, data=calendar)
    platform.get_calendar.return_value = SimpleNamespace(ok=True, data=calendar)
    platform.list_working_rules.return_value = SimpleNamespace(
        ok=True,
        data=[
            SimpleNamespace(weekday=0, is_working_day=True, computed_hours=6.5),
            SimpleNamespace(weekday=2, is_working_day=True, computed_hours=7.0),
            SimpleNamespace(weekday=0, is_working_day=False, computed_hours=0.0),
        ],
    )
    platform.list_exceptions.return_value = SimpleNamespace(
        ok=True,
        data=[
            SimpleNamespace(
                id="later",
                exception_date="2026-05-20",
                exception_type="holiday",
                name="Later",
            ),
            SimpleNamespace(
                id="ignored",
                exception_date="2026-05-10",
                exception_type="OVERTIME",
                name="Work",
            ),
            SimpleNamespace(
                id="early",
                exception_date="2026-05-01",
                exception_type="HOLIDAY",
                name="",
            ),
        ],
    )
    api = ProjectManagementSchedulingDesktopApi(platform_calendar_api=platform)

    assert api.list_calendars() is calendars
    assert api.list_calendars()[0] is calendar
    snapshot = api.get_calendar_snapshot("default")

    platform.get_default_calendar.assert_called_once_with()
    platform.get_calendar.assert_called_once_with("cal-1")
    assert snapshot.working_days == (2,)
    assert snapshot.hours_per_day == 6.5
    assert [holiday.id for holiday in snapshot.holidays] == ["early", "later"]
    assert snapshot.calendar_name == "Standard"
    assert not hasattr(snapshot, "summary_label")
    with pytest.raises(FrozenInstanceError):
        setattr(snapshot, "hours_per_day", 10.0)


def test_legacy_calendar_snapshot_is_detached_and_reuses_immutable_holidays() -> None:
    calendar = SimpleNamespace(
        id="legacy", name=" Local ", working_days={1, 3}, hours_per_day=7.5
    )
    holiday = WorkingCalendarHolidayDto("holiday", date(2026, 5, 1), "Holiday")
    service = Mock()
    service.get_calendar.return_value = calendar
    service.list_holidays.return_value = [holiday]
    api = ProjectManagementSchedulingDesktopApi(work_calendar_service=service)

    snapshot = api.get_calendar_snapshot()
    calendar.working_days.add(4)
    assert snapshot.working_days == (1, 3)
    assert snapshot.holidays[0] is holiday
    assert snapshot.calendar_name == "Local"
    assert snapshot.hours_per_day == 7.5
    assert api.list_calendars()[0].id == "legacy"
    assert (
        ProjectManagementSchedulingDesktopApi().get_calendar_snapshot().working_days
        == (0, 1, 2, 3, 4)
    )


@pytest.mark.parametrize(
    "category,error_type",
    [
        ("validation", ValueError),
        ("permission", PermissionError),
        ("system", RuntimeError),
    ],
)
def test_platform_calendar_errors_keep_their_categories(
    category: str, error_type: type[Exception]
) -> None:
    platform = Mock()
    platform.list_calendars.return_value = SimpleNamespace(
        ok=False, error=SimpleNamespace(category=category, message="Denied")
    )
    with pytest.raises(error_type, match="Denied"):
        ProjectManagementSchedulingDesktopApi(
            platform_calendar_api=platform
        ).list_calendars()
