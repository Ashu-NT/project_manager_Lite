from __future__ import annotations

from datetime import date

from src.api.desktop.platform import (
    PlatformCalendarDesktopApi,
    WorkingCalendarHolidayCreateCommand,
    WorkingCalendarUpdateCommand,
    WorkingDayCalculationCommand,
)
from src.api.desktop.runtime import build_desktop_api_registry


def _build_calendar_api(services) -> PlatformCalendarDesktopApi:
    return PlatformCalendarDesktopApi(
        work_calendar_service=services["work_calendar_service"],
        work_calendar_engine=services["work_calendar_engine"],
    )


def test_platform_calendar_desktop_api_manages_shared_calendar_and_holidays(services):
    api = _build_calendar_api(services)

    list_result = api.list_calendars()
    snapshot_result = api.get_calendar_snapshot()

    assert list_result.ok is True
    assert list_result.data is not None
    assert len(list_result.data) == 1
    assert list_result.data[0].label == "Default"
    assert snapshot_result.ok is True
    assert snapshot_result.data is not None
    assert snapshot_result.data.working_days[0].label == "Mon"

    update_result = api.update_calendar(
        WorkingCalendarUpdateCommand(
            working_days=(0, 1, 2, 3, 4, 5),
            hours_per_day=10.0,
        )
    )

    assert update_result.ok is True
    assert update_result.data is not None
    assert update_result.data.hours_per_day == 10.0
    assert update_result.data.working_days[5].checked is True

    holiday_result = api.add_holiday(
        WorkingCalendarHolidayCreateCommand(
            holiday_date=date(2026, 5, 1),
            name="Labor Day",
        )
    )

    assert holiday_result.ok is True
    assert holiday_result.data is not None
    assert holiday_result.data.name == "Labor Day"

    snapshot_after_holiday = api.get_calendar_snapshot()

    assert snapshot_after_holiday.ok is True
    assert snapshot_after_holiday.data is not None
    assert len(snapshot_after_holiday.data.holidays) == 1

    delete_result = api.delete_holiday(holiday_result.data.id)

    assert delete_result.ok is True

    final_snapshot = api.get_calendar_snapshot()

    assert final_snapshot.ok is True
    assert final_snapshot.data is not None
    assert final_snapshot.data.holidays == ()


def test_platform_calendar_desktop_api_calculates_working_days(services):
    api = _build_calendar_api(services)

    api.update_calendar(
        WorkingCalendarUpdateCommand(
            working_days=(0, 1, 2, 3, 4, 5),
            hours_per_day=8.0,
        )
    )

    result = api.calculate_working_day(
        WorkingDayCalculationCommand(
            start_date=date(2026, 5, 4),
            working_days=3,
        )
    )

    assert result.ok is True
    assert result.data is not None
    assert result.data.result_date == date(2026, 5, 6)


def test_build_desktop_api_registry_exposes_platform_calendar_api(services):
    registry = build_desktop_api_registry(services)

    result = registry.platform_calendar.get_calendar_snapshot()

    assert result.ok is True
    assert result.data is not None
    assert result.data.name == "Default"
