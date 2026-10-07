"""Month view's day-cell/day-details read projection -- this is where every
business-facing mapping (impact type -> tone/label, holiday distinction,
accessibility text, business-local "today") actually lives, so it is
covered directly here rather than by driving a full QML MonthGrid for every
scenario. See test_calendar_detail_qml_loads.py for the QML-compiles and
workspace-mount checks."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.ui_qml.platform.controllers.calendars.serializers import (
    serialize_calendar_day_view,
)


@dataclass
class _FakeDay:
    date: str
    is_working_day: bool
    base_hours: float = 8.0
    available_hours: float = 8.0
    status: str = "AVAILABLE"
    start_time: str = ""
    end_time: str = ""
    exception_type: str = ""
    exception_name: str = ""
    impact_type: str = ""


def test_normal_working_day_shows_hours_and_normal_tone() -> None:
    day = _FakeDay(date="2026-10-06", is_working_day=True, start_time="08:00", end_time="17:00")

    view = serialize_calendar_day_view(day, today_iso="2026-10-01")

    assert view["tone"] == "normal"
    assert view["isWorkingDay"] is True
    assert view["primaryLabel"] == "08:00–17:00"
    assert view["secondaryLabel"] == ""
    assert view["dayNumber"] == 6
    assert view["isToday"] is False


def test_weekend_non_working_day_shows_non_working_tone() -> None:
    day = _FakeDay(date="2026-10-04", is_working_day=False, available_hours=0.0)

    view = serialize_calendar_day_view(day, today_iso="2026-10-01")

    assert view["tone"] == "nonWorking"
    assert view["isWorkingDay"] is False
    assert view["primaryLabel"] == "Non-working"


def test_holiday_gets_its_own_tone_distinct_from_generic_unavailable() -> None:
    day = _FakeDay(
        date="2026-10-03",
        is_working_day=False,
        available_hours=0.0,
        exception_type="HOLIDAY",
        exception_name="German Unity Day",
        impact_type="UNAVAILABLE",
    )

    view = serialize_calendar_day_view(day, today_iso="2026-10-01")

    assert view["tone"] == "holiday"
    assert view["primaryLabel"] == "German Unity Day"
    assert view["secondaryLabel"] == "Non-working"
    assert view["exceptionTypeLabel"] == "Holiday"
    assert view["impactLabel"] == "Non-working"


def test_generic_shutdown_unavailable_day_is_not_tagged_as_holiday() -> None:
    day = _FakeDay(
        date="2026-12-31",
        is_working_day=False,
        available_hours=0.0,
        exception_type="SITE_CLOSED",
        exception_name="Site shutdown",
        impact_type="UNAVAILABLE",
    )

    view = serialize_calendar_day_view(day, today_iso="2026-10-01")

    assert view["tone"] == "unavailable"
    assert view["primaryLabel"] == "Site shutdown"


def test_reduced_capacity_day_shows_reduced_tone_and_hours() -> None:
    day = _FakeDay(
        date="2026-12-24",
        is_working_day=True,
        available_hours=4.0,
        start_time="08:00",
        end_time="12:00",
        exception_type="REDUCED_HOURS",
        exception_name="Reduced operating hours",
        impact_type="REDUCED_CAPACITY",
    )

    view = serialize_calendar_day_view(day, today_iso="2026-10-01")

    assert view["tone"] == "reduced"
    assert view["primaryLabel"] == "Reduced operating hours"
    assert view["secondaryLabel"] == "Reduced capacity"
    assert view["availableHours"] == 4.0


def test_extra_working_day_shows_extra_tone_and_hours_as_secondary() -> None:
    day = _FakeDay(
        date="2026-10-10",
        is_working_day=True,
        available_hours=5.0,
        start_time="09:00",
        end_time="14:00",
        exception_type="EXTRA_WORKING",
        exception_name="Extra working",
        impact_type="EXTRA_CAPACITY",
    )

    view = serialize_calendar_day_view(day, today_iso="2026-10-01")

    assert view["tone"] == "extra"
    assert view["secondaryLabel"] == "09:00–14:00"


def test_information_only_exception_uses_info_tone() -> None:
    day = _FakeDay(
        date="2026-10-20",
        is_working_day=True,
        start_time="08:00",
        end_time="17:00",
        exception_type="MEETING",
        exception_name="All-hands meeting",
        impact_type="INFORMATION_ONLY",
    )

    view = serialize_calendar_day_view(day, today_iso="2026-10-01")

    assert view["tone"] == "info"
    assert view["primaryLabel"] == "All-hands meeting"


def test_is_today_compares_against_business_local_today_not_a_default() -> None:
    day = _FakeDay(date="2026-10-01", is_working_day=True, start_time="08:00", end_time="17:00")

    assert serialize_calendar_day_view(day, today_iso="2026-10-01")["isToday"] is True
    assert serialize_calendar_day_view(day, today_iso="2026-10-02")["isToday"] is False


def test_accessibility_label_mentions_date_status_and_exception_name() -> None:
    day = _FakeDay(
        date="2026-10-03",
        is_working_day=False,
        available_hours=0.0,
        exception_type="HOLIDAY",
        exception_name="German Unity Day",
        impact_type="UNAVAILABLE",
    )

    label = serialize_calendar_day_view(day, today_iso="2026-10-01")["accessibilityLabel"]

    assert "Saturday" in label
    assert "03 October 2026" in label
    assert "Non-working" in label
    assert "German Unity Day" in label


def test_no_exception_vocabulary_leaks_as_raw_enum_text() -> None:
    day = _FakeDay(
        date="2026-10-03",
        is_working_day=False,
        available_hours=0.0,
        exception_type="MAINTENANCE_WINDOW",
        exception_name="",
        impact_type="UNAVAILABLE",
    )

    view = serialize_calendar_day_view(day, today_iso="2026-10-01")

    assert "_" not in view["exceptionTypeLabel"]
    assert view["exceptionTypeLabel"] == "Maintenance window"


@pytest.mark.parametrize("available_hours", [8.0, 4.5, 1.0, 0.0])
def test_available_hours_passes_through_as_a_plain_number(available_hours) -> None:
    # QML (PlatformCalendarDayDetails.qml) does the "8 h" vs "4.5 h" display
    # formatting; this only guarantees the raw value it formats is correct.
    day = _FakeDay(date="2026-10-06", is_working_day=True, available_hours=available_hours)
    view = serialize_calendar_day_view(day, today_iso="2026-10-01")
    assert view["availableHours"] == available_hours
