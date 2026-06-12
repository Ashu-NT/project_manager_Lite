"""Enterprise calendar domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone as dt_timezone
from enum import Enum
from src.core.platform.common.ids import generate_id


class CalendarType(str, Enum):
    GLOBAL = "GLOBAL"
    SITE = "SITE"
    DEPARTMENT = "DEPARTMENT"
    EMPLOYEE = "EMPLOYEE"
    PROJECT = "PROJECT"
    RESOURCE = "RESOURCE"


class ExceptionType(str, Enum):
    HOLIDAY = "HOLIDAY"
    SHUTDOWN = "SHUTDOWN"
    VACATION = "VACATION"
    SICK_LEAVE = "SICK_LEAVE"
    TRAINING = "TRAINING"
    MEETING = "MEETING"
    NON_WORKING = "NON_WORKING"
    EXTRA_WORKING = "EXTRA_WORKING"
    REDUCED_HOURS = "REDUCED_HOURS"
    OVERTIME = "OVERTIME"
    MAINTENANCE_WINDOW = "MAINTENANCE_WINDOW"
    SITE_CLOSED = "SITE_CLOSED"


class ImpactType(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    REDUCED_CAPACITY = "REDUCED_CAPACITY"
    EXTRA_CAPACITY = "EXTRA_CAPACITY"
    WORKING = "WORKING"
    INFORMATION_ONLY = "INFORMATION_ONLY"


class RecurringEventType(str, Enum):
    MEETING = "MEETING"
    TRAINING = "TRAINING"
    ADMIN = "ADMIN"
    MAINTENANCE = "MAINTENANCE"
    UNAVAILABLE = "UNAVAILABLE"
    ON_CALL = "ON_CALL"
    OVERTIME_WINDOW = "OVERTIME_WINDOW"
    SHIFT_BLOCK = "SHIFT_BLOCK"


class PatternType(str, Enum):
    STANDARD = "STANDARD"
    DAY_SHIFT = "DAY_SHIFT"
    NIGHT_SHIFT = "NIGHT_SHIFT"
    TWO_SHIFT = "TWO_SHIFT"
    THREE_SHIFT = "THREE_SHIFT"
    ROTATING = "ROTATING"
    FOUR_ON_FOUR_OFF = "FOUR_ON_FOUR_OFF"
    CUSTOM = "CUSTOM"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class PlatformCalendar:
    id: str
    organization_id: str
    code: str
    name: str
    calendar_type: str
    timezone: str = "UTC"
    description: str | None = None
    base_calendar_id: str | None = None
    scope_type: str | None = None
    scope_id: str | None = None
    locale: str | None = None
    is_default: bool = False
    is_active: bool = True
    effective_from: date | None = None
    effective_to: date | None = None
    priority: int = 0
    version: int = 1
    created_by: str | None = None
    created_at: datetime | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None

    @staticmethod
    def create(
        organization_id: str,
        code: str,
        name: str,
        calendar_type: str,
        *,
        timezone: str = "UTC",
        description: str | None = None,
        base_calendar_id: str | None = None,
        scope_type: str | None = None,
        scope_id: str | None = None,
        locale: str | None = None,
        is_default: bool = False,
        effective_from: date | None = None,
        effective_to: date | None = None,
        priority: int = 0,
        created_by: str | None = None,
    ) -> "PlatformCalendar":
        now = datetime.now(dt_timezone.utc)
        return PlatformCalendar(
            id=generate_id(),
            organization_id=organization_id,
            code=code,
            name=name,
            calendar_type=calendar_type,
            timezone=timezone,
            description=description,
            base_calendar_id=base_calendar_id,
            scope_type=scope_type,
            scope_id=scope_id,
            locale=locale,
            is_default=is_default,
            is_active=True,
            effective_from=effective_from,
            effective_to=effective_to,
            priority=priority,
            version=1,
            created_by=created_by,
            created_at=now,
            updated_by=created_by,
            updated_at=now,
        )


@dataclass
class CalendarWorkingRule:
    id: str
    calendar_id: str
    weekday: int
    is_working_day: bool = True
    start_time: time | None = None
    end_time: time | None = None
    break_start_time: time | None = None
    break_end_time: time | None = None
    break_minutes: int = 0
    hours_override: float | None = None
    shift_code: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    priority: int = 0

    @staticmethod
    def create(
        calendar_id: str,
        weekday: int,
        *,
        is_working_day: bool = True,
        start_time: time | None = None,
        end_time: time | None = None,
        break_start_time: time | None = None,
        break_end_time: time | None = None,
        break_minutes: int = 0,
        hours_override: float | None = None,
        shift_code: str | None = None,
        effective_from: date | None = None,
        effective_to: date | None = None,
        priority: int = 0,
    ) -> "CalendarWorkingRule":
        return CalendarWorkingRule(
            id=generate_id(),
            calendar_id=calendar_id,
            weekday=weekday,
            is_working_day=is_working_day,
            start_time=start_time,
            end_time=end_time,
            break_start_time=break_start_time,
            break_end_time=break_end_time,
            break_minutes=break_minutes,
            hours_override=hours_override,
            shift_code=shift_code,
            effective_from=effective_from,
            effective_to=effective_to,
            priority=priority,
        )

    def compute_hours(self) -> float:
        if not self.is_working_day:
            return 0.0
        if self.hours_override is not None:
            return self.hours_override
        if self.start_time and self.end_time:
            start_min = self.start_time.hour * 60 + self.start_time.minute
            end_min = self.end_time.hour * 60 + self.end_time.minute
            total_min = max(0, end_min - start_min - self.break_minutes)
            return total_min / 60.0
        return 8.0


@dataclass
class CalendarException:
    id: str
    calendar_id: str
    exception_date: date
    exception_type: str
    name: str
    impact_type: str
    scope_type: str | None = None
    scope_id: str | None = None
    description: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    hours_override: float | None = None
    priority: int = 0
    approval_status: str = "APPROVED"
    approved_by: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None

    @staticmethod
    def create(
        calendar_id: str,
        exception_date: date,
        exception_type: str,
        name: str,
        impact_type: str,
        *,
        scope_type: str | None = None,
        scope_id: str | None = None,
        description: str | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
        hours_override: float | None = None,
        priority: int = 0,
        approval_status: str = "APPROVED",
        created_by: str | None = None,
    ) -> "CalendarException":
        now = datetime.utcnow()
        return CalendarException(
            id=generate_id(),
            calendar_id=calendar_id,
            exception_date=exception_date,
            exception_type=exception_type,
            name=name,
            impact_type=impact_type,
            scope_type=scope_type,
            scope_id=scope_id,
            description=description,
            start_time=start_time,
            end_time=end_time,
            hours_override=hours_override,
            priority=priority,
            approval_status=approval_status,
            created_by=created_by,
            created_at=now,
            updated_by=created_by,
            updated_at=now,
        )

    def compute_hours(self) -> float:
        if self.hours_override is not None:
            return self.hours_override
        if self.start_time and self.end_time:
            start_min = self.start_time.hour * 60 + self.start_time.minute
            end_min = self.end_time.hour * 60 + self.end_time.minute
            return max(0, end_min - start_min) / 60.0
        return 0.0


@dataclass
class CalendarRecurringEvent:
    id: str
    calendar_id: str
    title: str
    event_type: str
    recurrence_rule: str
    start_time: time
    end_time: time
    impact_type: str
    effective_from: date
    scope_type: str | None = None
    scope_id: str | None = None
    capacity_impact_percent: float | None = None
    effective_to: date | None = None
    is_active: bool = True
    priority: int = 0

    @staticmethod
    def create(
        calendar_id: str,
        title: str,
        event_type: str,
        recurrence_rule: str,
        start_time: time,
        end_time: time,
        impact_type: str,
        effective_from: date,
        *,
        scope_type: str | None = None,
        scope_id: str | None = None,
        capacity_impact_percent: float | None = None,
        effective_to: date | None = None,
        priority: int = 0,
    ) -> "CalendarRecurringEvent":
        return CalendarRecurringEvent(
            id=generate_id(),
            calendar_id=calendar_id,
            title=title,
            event_type=event_type,
            recurrence_rule=recurrence_rule,
            start_time=start_time,
            end_time=end_time,
            impact_type=impact_type,
            effective_from=effective_from,
            scope_type=scope_type,
            scope_id=scope_id,
            capacity_impact_percent=capacity_impact_percent,
            effective_to=effective_to,
            is_active=True,
            priority=priority,
        )

    def duration_hours(self) -> float:
        start_min = self.start_time.hour * 60 + self.start_time.minute
        end_min = self.end_time.hour * 60 + self.end_time.minute
        return max(0, end_min - start_min) / 60.0


@dataclass
class ShiftPattern:
    id: str
    organization_id: str
    code: str
    name: str
    pattern_type: str
    timezone: str = "UTC"
    description: str | None = None
    rotation_cycle_days: int | None = None
    is_active: bool = True

    @staticmethod
    def create(
        organization_id: str,
        code: str,
        name: str,
        pattern_type: str,
        *,
        timezone: str = "UTC",
        description: str | None = None,
        rotation_cycle_days: int | None = None,
    ) -> "ShiftPattern":
        return ShiftPattern(
            id=generate_id(),
            organization_id=organization_id,
            code=code,
            name=name,
            pattern_type=pattern_type,
            timezone=timezone,
            description=description,
            rotation_cycle_days=rotation_cycle_days,
            is_active=True,
        )


@dataclass
class ShiftPatternDay:
    id: str
    shift_pattern_id: str
    day_offset: int
    is_working_day: bool = True
    start_time: time | None = None
    end_time: time | None = None
    break_minutes: int = 0
    hours: float | None = None
    shift_label: str | None = None

    @staticmethod
    def create(
        shift_pattern_id: str,
        day_offset: int,
        *,
        is_working_day: bool = True,
        start_time: time | None = None,
        end_time: time | None = None,
        break_minutes: int = 0,
        hours: float | None = None,
        shift_label: str | None = None,
    ) -> "ShiftPatternDay":
        return ShiftPatternDay(
            id=generate_id(),
            shift_pattern_id=shift_pattern_id,
            day_offset=day_offset,
            is_working_day=is_working_day,
            start_time=start_time,
            end_time=end_time,
            break_minutes=break_minutes,
            hours=hours,
            shift_label=shift_label,
        )


@dataclass
class SiteCalendarAssignment:
    id: str
    site_id: str
    calendar_id: str
    effective_from: date | None = None
    effective_to: date | None = None
    is_default: bool = False
    priority: int = 0

    @staticmethod
    def create(
        site_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> "SiteCalendarAssignment":
        return SiteCalendarAssignment(
            id=generate_id(),
            site_id=site_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )


@dataclass
class DepartmentCalendarAssignment:
    id: str
    department_id: str
    calendar_id: str
    effective_from: date | None = None
    effective_to: date | None = None
    is_default: bool = False
    priority: int = 0

    @staticmethod
    def create(
        department_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> "DepartmentCalendarAssignment":
        return DepartmentCalendarAssignment(
            id=generate_id(),
            department_id=department_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )


@dataclass
class EmployeeCalendarAssignment:
    id: str
    employee_id: str
    calendar_id: str
    effective_from: date | None = None
    effective_to: date | None = None
    is_default: bool = False
    priority: int = 0

    @staticmethod
    def create(
        employee_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> "EmployeeCalendarAssignment":
        return EmployeeCalendarAssignment(
            id=generate_id(),
            employee_id=employee_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )


__all__ = [
    "ApprovalStatus",
    "CalendarException",
    "CalendarRecurringEvent",
    "CalendarType",
    "CalendarWorkingRule",
    "DepartmentCalendarAssignment",
    "EmployeeCalendarAssignment",
    "ExceptionType",
    "ImpactType",
    "PatternType",
    "PlatformCalendar",
    "RecurringEventType",
    "ShiftPattern",
    "ShiftPatternDay",
    "SiteCalendarAssignment",
]
