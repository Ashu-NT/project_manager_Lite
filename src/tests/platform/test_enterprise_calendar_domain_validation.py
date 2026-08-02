from __future__ import annotations

from datetime import date, time

import pytest

from src.core.platform.calendar.domain.enterprise_calendar import (
    CalendarException,
    CalendarRecurringEvent,
    CalendarWorkingRule,
    DepartmentCalendarAssignment,
    EmployeeCalendarAssignment,
    PlatformCalendar,
    ShiftPattern,
    ShiftPatternDay,
    SiteCalendarAssignment,
)
from src.core.platform.common.exceptions import ValidationError


def test_platform_calendar_dto_normalizes_and_validates_fields() -> None:
    calendar = PlatformCalendar.create(
        organization_id="  org-1  ",
        code="  ops-main  ",
        name="  Operations Main  ",
        calendar_type="site",
        timezone="",
        description="  Core working calendar  ",
        scope_type="  SITE  ",
        scope_id="  site-1  ",
        locale="  en-US  ",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        priority="3",
        created_by="  ada  ",
    )

    assert calendar.organization_id == "org-1"
    assert calendar.code == "OPS-MAIN"
    assert calendar.name == "Operations Main"
    assert calendar.calendar_type == "SITE"
    assert calendar.timezone == "UTC"
    assert calendar.description == "Core working calendar"
    assert calendar.scope_type == "site"
    assert calendar.scope_id == "site-1"
    assert calendar.locale == "en-US"
    assert calendar.priority == 3
    assert calendar.created_by == "ada"

    with pytest.raises(ValidationError) as exc_range:
        PlatformCalendar.create(
            organization_id="org-1",
            code="OPS-BAD",
            name="Bad Calendar",
            calendar_type="GLOBAL",
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )
    assert exc_range.value.code == "CALENDAR_EFFECTIVE_RANGE_INVALID"


def test_calendar_exception_dto_normalizes_aliases_and_validates_time_window() -> None:
    exception = CalendarException.create(
        calendar_id="  cal-1  ",
        exception_date=date(2026, 12, 25),
        exception_type="holiday",
        name="  Christmas Shutdown  ",
        impact_type="non_working",
        scope_type="  SITE  ",
        scope_id="  site-1  ",
        description="  Full day closure  ",
        start_time=time(8, 0),
        end_time=time(17, 0),
        hours_override="0",
        priority="2",
        approval_status="approved",
        created_by="  ada  ",
    )

    assert exception.calendar_id == "cal-1"
    assert exception.exception_type == "HOLIDAY"
    assert exception.name == "Christmas Shutdown"
    assert exception.impact_type == "UNAVAILABLE"
    assert exception.scope_type == "site"
    assert exception.scope_id == "site-1"
    assert exception.description == "Full day closure"
    assert exception.hours_override == 0.0
    assert exception.priority == 2
    assert exception.approval_status == "APPROVED"
    assert exception.created_by == "ada"

    with pytest.raises(ValidationError) as exc_time:
        CalendarException.create(
            calendar_id="cal-1",
            exception_date=date(2026, 12, 25),
            exception_type="HOLIDAY",
            name="Bad Window",
            impact_type="UNAVAILABLE",
            start_time=time(12, 0),
            end_time=time(12, 0),
        )
    assert exc_time.value.code == "CALENDAR_EXCEPTION_TIME_RANGE_INVALID"


def test_recurring_event_dto_normalizes_aliases_and_validates_ranges() -> None:
    event = CalendarRecurringEvent.create(
        calendar_id="  cal-1  ",
        title="  Night Shift  ",
        event_type="shift",
        recurrence_rule="  FREQ=WEEKLY;BYDAY=MO  ",
        start_time=time(22, 0),
        end_time=time(23, 0),
        impact_type="non_working",
        effective_from=date(2026, 1, 1),
        scope_type="  department  ",
        scope_id="  dept-1  ",
        capacity_impact_percent="25",
        effective_to=date(2026, 12, 31),
        priority="5",
    )

    assert event.calendar_id == "cal-1"
    assert event.title == "Night Shift"
    assert event.event_type == "SHIFT_BLOCK"
    assert event.recurrence_rule == "FREQ=WEEKLY;BYDAY=MO"
    assert event.impact_type == "UNAVAILABLE"
    assert event.scope_type == "department"
    assert event.scope_id == "dept-1"
    assert event.capacity_impact_percent == 25.0
    assert event.priority == 5

    with pytest.raises(ValidationError) as exc_range:
        CalendarRecurringEvent.create(
            calendar_id="cal-1",
            title="Bad Range",
            event_type="MEETING",
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
            start_time=time(9, 0),
            end_time=time(10, 0),
            impact_type="REDUCED_CAPACITY",
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )
    assert exc_range.value.code == "RECURRING_EVENT_DATE_RANGE_INVALID"


def test_shift_pattern_and_day_dto_normalize_aliases_and_validate_ranges() -> None:
    pattern = ShiftPattern.create(
        organization_id="  org-1  ",
        code="  rot-a  ",
        name="  Rotating A  ",
        pattern_type="fixed",
        timezone="",
        description="  Primary team rotation  ",
        rotation_cycle_days="4",
    )

    assert pattern.organization_id == "org-1"
    assert pattern.code == "ROT-A"
    assert pattern.name == "Rotating A"
    assert pattern.pattern_type == "STANDARD"
    assert pattern.timezone == "UTC"
    assert pattern.description == "Primary team rotation"
    assert pattern.rotation_cycle_days == 4

    day = ShiftPatternDay.create(
        shift_pattern_id="  pattern-1  ",
        day_offset="0",
        start_time=time(6, 0),
        end_time=time(14, 0),
        break_minutes="30",
        hours="7.5",
        shift_label="  Day  ",
    )

    assert day.shift_pattern_id == "pattern-1"
    assert day.day_offset == 0
    assert day.break_minutes == 30
    assert day.hours == 7.5
    assert day.shift_label == "Day"

    with pytest.raises(ValidationError) as exc_day_offset:
        ShiftPatternDay.create(
            shift_pattern_id="pattern-1",
            day_offset=-1,
        )
    assert exc_day_offset.value.code == "SHIFT_PATTERN_DAY_OFFSET_INVALID"


def test_calendar_working_rule_dto_normalizes_and_validates_ranges() -> None:
    rule = CalendarWorkingRule.create(
        calendar_id="  cal-1  ",
        weekday="1",
        is_working_day=True,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_start_time=time(12, 0),
        break_end_time=time(12, 30),
        break_minutes="30",
        hours_override="7.5",
        shift_code="  day  ",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        priority="2",
    )

    assert rule.calendar_id == "cal-1"
    assert rule.weekday == 1
    assert rule.break_minutes == 30
    assert rule.hours_override == 7.5
    assert rule.shift_code == "day"
    assert rule.priority == 2

    with pytest.raises(ValidationError) as exc_id:
        CalendarWorkingRule(id=" ", calendar_id="cal-1", weekday=1)
    assert exc_id.value.code == "CALENDAR_RULE_ID_REQUIRED"

    with pytest.raises(ValidationError) as exc_weekday:
        CalendarWorkingRule.create(
            calendar_id="cal-1",
            weekday=7,
        )
    assert exc_weekday.value.code == "CALENDAR_RULE_WEEKDAY_INVALID"

    with pytest.raises(ValidationError) as exc_hours:
        CalendarWorkingRule.create(
            calendar_id="cal-1",
            weekday=1,
            hours_override="-1",
        )
    assert exc_hours.value.code == "CALENDAR_RULE_HOURS_OVERRIDE_INVALID"

    with pytest.raises(ValidationError) as exc_time:
        CalendarWorkingRule.create(
            calendar_id="cal-1",
            weekday=1,
            start_time=time(17, 0),
            end_time=time(8, 0),
        )
    assert exc_time.value.code == "CALENDAR_RULE_TIME_RANGE_INVALID"

    with pytest.raises(ValidationError) as exc_range:
        CalendarWorkingRule.create(
            calendar_id="cal-1",
            weekday=1,
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )
    assert exc_range.value.code == "CALENDAR_RULE_EFFECTIVE_RANGE_INVALID"


def test_calendar_assignment_dtos_normalize_and_validate_ranges() -> None:
    site_assignment = SiteCalendarAssignment.create(
        site_id="  site-1  ",
        calendar_id="  cal-1  ",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        priority="2",
    )
    department_assignment = DepartmentCalendarAssignment.create(
        department_id="  dept-1  ",
        calendar_id="  cal-1  ",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        priority="3",
    )
    employee_assignment = EmployeeCalendarAssignment.create(
        employee_id="  emp-1  ",
        calendar_id="  cal-1  ",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        priority="4",
    )

    assert site_assignment.site_id == "site-1"
    assert site_assignment.calendar_id == "cal-1"
    assert site_assignment.priority == 2
    assert department_assignment.department_id == "dept-1"
    assert department_assignment.priority == 3
    assert employee_assignment.employee_id == "emp-1"
    assert employee_assignment.priority == 4

    with pytest.raises(ValidationError) as exc_site_required:
        SiteCalendarAssignment.create(site_id=" ", calendar_id="cal-1")
    assert exc_site_required.value.code == "SITE_CALENDAR_ASSIGNMENT_SITE_REQUIRED"

    with pytest.raises(ValidationError) as exc_calendar_required:
        SiteCalendarAssignment.create(site_id="site-1", calendar_id=" ")
    assert exc_calendar_required.value.code == "SITE_CALENDAR_ASSIGNMENT_CALENDAR_REQUIRED"

    with pytest.raises(ValidationError) as exc_site_range:
        SiteCalendarAssignment.create(
            site_id="site-1",
            calendar_id="cal-1",
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )
    assert exc_site_range.value.code == "SITE_CALENDAR_ASSIGNMENT_DATE_RANGE_INVALID"

    with pytest.raises(ValidationError) as exc_department_required:
        DepartmentCalendarAssignment.create(department_id=" ", calendar_id="cal-1")
    assert (
        exc_department_required.value.code
        == "DEPARTMENT_CALENDAR_ASSIGNMENT_DEPARTMENT_REQUIRED"
    )

    with pytest.raises(ValidationError) as exc_department_range:
        DepartmentCalendarAssignment.create(
            department_id="dept-1",
            calendar_id="cal-1",
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )
    assert (
        exc_department_range.value.code
        == "DEPARTMENT_CALENDAR_ASSIGNMENT_DATE_RANGE_INVALID"
    )

    with pytest.raises(ValidationError) as exc_employee_required:
        EmployeeCalendarAssignment.create(employee_id=" ", calendar_id="cal-1")
    assert (
        exc_employee_required.value.code
        == "EMPLOYEE_CALENDAR_ASSIGNMENT_EMPLOYEE_REQUIRED"
    )

    with pytest.raises(ValidationError) as exc_employee_range:
        EmployeeCalendarAssignment.create(
            employee_id="emp-1",
            calendar_id="cal-1",
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )
    assert exc_employee_range.value.code == "EMPLOYEE_CALENDAR_ASSIGNMENT_DATE_RANGE_INVALID"
