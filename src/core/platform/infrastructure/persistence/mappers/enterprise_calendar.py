"""Mappers between enterprise calendar domain objects and ORM rows."""

from __future__ import annotations

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
from src.core.platform.infrastructure.persistence.orm.enterprise_calendar import (
    CalendarExceptionORM,
    CalendarRecurringEventORM,
    CalendarWorkingRuleORM,
    DepartmentCalendarAssignmentORM,
    EmployeeCalendarAssignmentORM,
    PlatformCalendarORM,
    ShiftPatternDayORM,
    ShiftPatternORM,
    SiteCalendarAssignmentORM,
)


# ---------------------------------------------------------------------------
# PlatformCalendar
# ---------------------------------------------------------------------------


def platform_calendar_from_orm(obj: PlatformCalendarORM) -> PlatformCalendar:
    return PlatformCalendar(
        id=obj.id,
        organization_id=obj.organization_id,
        code=obj.code,
        name=obj.name,
        calendar_type=obj.calendar_type,
        timezone=obj.timezone,
        description=obj.description,
        base_calendar_id=obj.base_calendar_id,
        scope_type=obj.scope_type,
        scope_id=obj.scope_id,
        locale=obj.locale,
        is_default=obj.is_default,
        is_active=obj.is_active,
        effective_from=obj.effective_from,
        effective_to=obj.effective_to,
        priority=obj.priority,
        version=obj.version,
        created_by=obj.created_by,
        created_at=obj.created_at,
        updated_by=obj.updated_by,
        updated_at=obj.updated_at,
    )


def platform_calendar_to_orm(cal: PlatformCalendar) -> PlatformCalendarORM:
    return PlatformCalendarORM(
        id=cal.id,
        organization_id=cal.organization_id,
        code=cal.code,
        name=cal.name,
        calendar_type=cal.calendar_type,
        timezone=cal.timezone,
        description=cal.description,
        base_calendar_id=cal.base_calendar_id,
        scope_type=cal.scope_type,
        scope_id=cal.scope_id,
        locale=cal.locale,
        is_default=cal.is_default,
        is_active=cal.is_active,
        effective_from=cal.effective_from,
        effective_to=cal.effective_to,
        priority=cal.priority,
        version=cal.version,
        created_by=cal.created_by,
        created_at=cal.created_at,
        updated_by=cal.updated_by,
        updated_at=cal.updated_at,
    )


# ---------------------------------------------------------------------------
# CalendarWorkingRule
# ---------------------------------------------------------------------------


def working_rule_from_orm(obj: CalendarWorkingRuleORM) -> CalendarWorkingRule:
    return CalendarWorkingRule(
        id=obj.id,
        calendar_id=obj.calendar_id,
        weekday=obj.weekday,
        is_working_day=obj.is_working_day,
        start_time=obj.start_time,
        end_time=obj.end_time,
        break_start_time=obj.break_start_time,
        break_end_time=obj.break_end_time,
        break_minutes=obj.break_minutes,
        hours_override=obj.hours_override,
        shift_code=obj.shift_code,
        effective_from=obj.effective_from,
        effective_to=obj.effective_to,
        priority=obj.priority,
    )


def working_rule_to_orm(rule: CalendarWorkingRule) -> CalendarWorkingRuleORM:
    return CalendarWorkingRuleORM(
        id=rule.id,
        calendar_id=rule.calendar_id,
        weekday=rule.weekday,
        is_working_day=rule.is_working_day,
        start_time=rule.start_time,
        end_time=rule.end_time,
        break_start_time=rule.break_start_time,
        break_end_time=rule.break_end_time,
        break_minutes=rule.break_minutes,
        hours_override=rule.hours_override,
        shift_code=rule.shift_code,
        effective_from=rule.effective_from,
        effective_to=rule.effective_to,
        priority=rule.priority,
    )


# ---------------------------------------------------------------------------
# CalendarException
# ---------------------------------------------------------------------------


def calendar_exception_from_orm(obj: CalendarExceptionORM) -> CalendarException:
    return CalendarException(
        id=obj.id,
        calendar_id=obj.calendar_id,
        exception_date=obj.exception_date,
        exception_type=obj.exception_type,
        name=obj.name,
        impact_type=obj.impact_type,
        scope_type=obj.scope_type,
        scope_id=obj.scope_id,
        description=obj.description,
        start_time=obj.start_time,
        end_time=obj.end_time,
        hours_override=obj.hours_override,
        priority=obj.priority,
        approval_status=obj.approval_status,
        approved_by=obj.approved_by,
        created_by=obj.created_by,
        created_at=obj.created_at,
        updated_by=obj.updated_by,
        updated_at=obj.updated_at,
    )


def calendar_exception_to_orm(exc: CalendarException) -> CalendarExceptionORM:
    return CalendarExceptionORM(
        id=exc.id,
        calendar_id=exc.calendar_id,
        exception_date=exc.exception_date,
        exception_type=exc.exception_type,
        name=exc.name,
        impact_type=exc.impact_type,
        scope_type=exc.scope_type,
        scope_id=exc.scope_id,
        description=exc.description,
        start_time=exc.start_time,
        end_time=exc.end_time,
        hours_override=exc.hours_override,
        priority=exc.priority,
        approval_status=exc.approval_status,
        approved_by=exc.approved_by,
        created_by=exc.created_by,
        created_at=exc.created_at,
        updated_by=exc.updated_by,
        updated_at=exc.updated_at,
    )


# ---------------------------------------------------------------------------
# CalendarRecurringEvent
# ---------------------------------------------------------------------------


def recurring_event_from_orm(obj: CalendarRecurringEventORM) -> CalendarRecurringEvent:
    return CalendarRecurringEvent(
        id=obj.id,
        calendar_id=obj.calendar_id,
        title=obj.title,
        event_type=obj.event_type,
        recurrence_rule=obj.recurrence_rule,
        start_time=obj.start_time,
        end_time=obj.end_time,
        impact_type=obj.impact_type,
        effective_from=obj.effective_from,
        scope_type=obj.scope_type,
        scope_id=obj.scope_id,
        capacity_impact_percent=obj.capacity_impact_percent,
        effective_to=obj.effective_to,
        is_active=obj.is_active,
        priority=obj.priority,
    )


def recurring_event_to_orm(event: CalendarRecurringEvent) -> CalendarRecurringEventORM:
    return CalendarRecurringEventORM(
        id=event.id,
        calendar_id=event.calendar_id,
        title=event.title,
        event_type=event.event_type,
        recurrence_rule=event.recurrence_rule,
        start_time=event.start_time,
        end_time=event.end_time,
        impact_type=event.impact_type,
        effective_from=event.effective_from,
        scope_type=event.scope_type,
        scope_id=event.scope_id,
        capacity_impact_percent=event.capacity_impact_percent,
        effective_to=event.effective_to,
        is_active=event.is_active,
        priority=event.priority,
    )


# ---------------------------------------------------------------------------
# ShiftPattern + ShiftPatternDay
# ---------------------------------------------------------------------------


def shift_pattern_from_orm(obj: ShiftPatternORM) -> ShiftPattern:
    return ShiftPattern(
        id=obj.id,
        organization_id=obj.organization_id,
        code=obj.code,
        name=obj.name,
        pattern_type=obj.pattern_type,
        timezone=obj.timezone,
        description=obj.description,
        rotation_cycle_days=obj.rotation_cycle_days,
        is_active=obj.is_active,
    )


def shift_pattern_to_orm(pattern: ShiftPattern) -> ShiftPatternORM:
    return ShiftPatternORM(
        id=pattern.id,
        organization_id=pattern.organization_id,
        code=pattern.code,
        name=pattern.name,
        pattern_type=pattern.pattern_type,
        timezone=pattern.timezone,
        description=pattern.description,
        rotation_cycle_days=pattern.rotation_cycle_days,
        is_active=pattern.is_active,
    )


def shift_pattern_day_from_orm(obj: ShiftPatternDayORM) -> ShiftPatternDay:
    return ShiftPatternDay(
        id=obj.id,
        shift_pattern_id=obj.shift_pattern_id,
        day_offset=obj.day_offset,
        is_working_day=obj.is_working_day,
        start_time=obj.start_time,
        end_time=obj.end_time,
        break_minutes=obj.break_minutes,
        hours=obj.hours,
        shift_label=obj.shift_label,
    )


def shift_pattern_day_to_orm(day: ShiftPatternDay) -> ShiftPatternDayORM:
    return ShiftPatternDayORM(
        id=day.id,
        shift_pattern_id=day.shift_pattern_id,
        day_offset=day.day_offset,
        is_working_day=day.is_working_day,
        start_time=day.start_time,
        end_time=day.end_time,
        break_minutes=day.break_minutes,
        hours=day.hours,
        shift_label=day.shift_label,
    )


# ---------------------------------------------------------------------------
# Assignment tables
# ---------------------------------------------------------------------------


def site_assignment_from_orm(obj: SiteCalendarAssignmentORM) -> SiteCalendarAssignment:
    return SiteCalendarAssignment(
        id=obj.id,
        site_id=obj.site_id,
        calendar_id=obj.calendar_id,
        effective_from=obj.effective_from,
        effective_to=obj.effective_to,
        is_default=obj.is_default,
        priority=obj.priority,
    )


def site_assignment_to_orm(a: SiteCalendarAssignment) -> SiteCalendarAssignmentORM:
    return SiteCalendarAssignmentORM(
        id=a.id,
        site_id=a.site_id,
        calendar_id=a.calendar_id,
        effective_from=a.effective_from,
        effective_to=a.effective_to,
        is_default=a.is_default,
        priority=a.priority,
    )


def dept_assignment_from_orm(
    obj: DepartmentCalendarAssignmentORM,
) -> DepartmentCalendarAssignment:
    return DepartmentCalendarAssignment(
        id=obj.id,
        department_id=obj.department_id,
        calendar_id=obj.calendar_id,
        effective_from=obj.effective_from,
        effective_to=obj.effective_to,
        is_default=obj.is_default,
        priority=obj.priority,
    )


def dept_assignment_to_orm(
    a: DepartmentCalendarAssignment,
) -> DepartmentCalendarAssignmentORM:
    return DepartmentCalendarAssignmentORM(
        id=a.id,
        department_id=a.department_id,
        calendar_id=a.calendar_id,
        effective_from=a.effective_from,
        effective_to=a.effective_to,
        is_default=a.is_default,
        priority=a.priority,
    )


def employee_assignment_from_orm(
    obj: EmployeeCalendarAssignmentORM,
) -> EmployeeCalendarAssignment:
    return EmployeeCalendarAssignment(
        id=obj.id,
        employee_id=obj.employee_id,
        calendar_id=obj.calendar_id,
        effective_from=obj.effective_from,
        effective_to=obj.effective_to,
        is_default=obj.is_default,
        priority=obj.priority,
    )


def employee_assignment_to_orm(
    a: EmployeeCalendarAssignment,
) -> EmployeeCalendarAssignmentORM:
    return EmployeeCalendarAssignmentORM(
        id=a.id,
        employee_id=a.employee_id,
        calendar_id=a.calendar_id,
        effective_from=a.effective_from,
        effective_to=a.effective_to,
        is_default=a.is_default,
        priority=a.priority,
    )


__all__ = [
    "calendar_exception_from_orm",
    "calendar_exception_to_orm",
    "dept_assignment_from_orm",
    "dept_assignment_to_orm",
    "employee_assignment_from_orm",
    "employee_assignment_to_orm",
    "platform_calendar_from_orm",
    "platform_calendar_to_orm",
    "recurring_event_from_orm",
    "recurring_event_to_orm",
    "shift_pattern_day_from_orm",
    "shift_pattern_day_to_orm",
    "shift_pattern_from_orm",
    "shift_pattern_to_orm",
    "site_assignment_from_orm",
    "site_assignment_to_orm",
    "working_rule_from_orm",
    "working_rule_to_orm",
]
