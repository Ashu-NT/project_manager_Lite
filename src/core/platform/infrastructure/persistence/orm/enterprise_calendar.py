"""Platform enterprise calendar ORM models."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class PlatformCalendarORM(Base):
    __tablename__ = "platform_calendars"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="ux_platform_calendars_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    calendar_type: Mapped[str] = mapped_column(String(64), nullable=False)
    base_calendar_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("platform_calendars.id", ondelete="SET NULL"),
        nullable=True,
    )
    scope_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scope_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(128), nullable=False, default="UTC", server_default="UTC"
    )
    locale: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_platform_calendars_tenant", PlatformCalendarORM.tenant_id)
Index("idx_platform_calendars_org", PlatformCalendarORM.organization_id)
Index("idx_platform_calendars_type", PlatformCalendarORM.calendar_type)
Index(
    "idx_platform_calendars_scope",
    PlatformCalendarORM.scope_type,
    PlatformCalendarORM.scope_id,
)
Index(
    "idx_platform_calendars_active",
    PlatformCalendarORM.organization_id,
    PlatformCalendarORM.is_active,
)


class CalendarWorkingRuleORM(Base):
    __tablename__ = "calendar_working_rules"
    __table_args__ = (
        UniqueConstraint("calendar_id", "weekday", name="ux_cal_working_rules_cal_day"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    calendar_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("platform_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    is_working_day: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    break_start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    break_end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    break_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    hours_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shift_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


Index("idx_cal_working_rules_calendar", CalendarWorkingRuleORM.calendar_id)


class CalendarExceptionORM(Base):
    __tablename__ = "calendar_exceptions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    calendar_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("platform_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scope_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    exception_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    hours_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    impact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    approval_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="APPROVED", server_default="APPROVED"
    )
    approved_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_cal_exceptions_calendar", CalendarExceptionORM.calendar_id)
Index("idx_cal_exceptions_date", CalendarExceptionORM.exception_date)
Index(
    "idx_cal_exceptions_scope",
    CalendarExceptionORM.scope_type,
    CalendarExceptionORM.scope_id,
)
Index(
    "idx_cal_exceptions_cal_date",
    CalendarExceptionORM.calendar_id,
    CalendarExceptionORM.exception_date,
)


class CalendarRecurringEventORM(Base):
    __tablename__ = "calendar_recurring_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    calendar_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("platform_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scope_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    recurrence_rule: Mapped[str] = mapped_column(String(512), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    impact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    capacity_impact_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


Index("idx_cal_recurring_calendar", CalendarRecurringEventORM.calendar_id)
Index(
    "idx_cal_recurring_scope",
    CalendarRecurringEventORM.scope_type,
    CalendarRecurringEventORM.scope_id,
)
Index("idx_cal_recurring_active", CalendarRecurringEventORM.is_active)


class ShiftPatternORM(Base):
    __tablename__ = "shift_patterns"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="ux_shift_patterns_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pattern_type: Mapped[str] = mapped_column(String(64), nullable=False)
    rotation_cycle_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(128), nullable=False, default="UTC", server_default="UTC"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )


Index("idx_shift_patterns_tenant", ShiftPatternORM.tenant_id)
Index("idx_shift_patterns_org", ShiftPatternORM.organization_id)
Index("idx_shift_patterns_active", ShiftPatternORM.organization_id, ShiftPatternORM.is_active)


class ShiftPatternDayORM(Base):
    __tablename__ = "shift_pattern_days"
    __table_args__ = (
        UniqueConstraint(
            "shift_pattern_id", "day_offset", name="ux_shift_pattern_days_offset"
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    shift_pattern_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("shift_patterns.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    is_working_day: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    break_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shift_label: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


Index("idx_shift_pattern_days_pattern", ShiftPatternDayORM.shift_pattern_id)


# ---------------------------------------------------------------------------
# Assignment tables
# ---------------------------------------------------------------------------


class SiteCalendarAssignmentORM(Base):
    __tablename__ = "site_calendar_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    site_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    calendar_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("platform_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


Index("idx_site_cal_assign_site", SiteCalendarAssignmentORM.site_id)
Index("idx_site_cal_assign_cal", SiteCalendarAssignmentORM.calendar_id)


class DepartmentCalendarAssignmentORM(Base):
    __tablename__ = "department_calendar_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    department_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
    )
    calendar_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("platform_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


Index("idx_dept_cal_assign_dept", DepartmentCalendarAssignmentORM.department_id)
Index("idx_dept_cal_assign_cal", DepartmentCalendarAssignmentORM.calendar_id)


class EmployeeCalendarAssignmentORM(Base):
    __tablename__ = "employee_calendar_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    employee_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    calendar_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("platform_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


Index("idx_emp_cal_assign_emp", EmployeeCalendarAssignmentORM.employee_id)
Index("idx_emp_cal_assign_cal", EmployeeCalendarAssignmentORM.calendar_id)


__all__ = [
    "CalendarExceptionORM",
    "CalendarRecurringEventORM",
    "CalendarWorkingRuleORM",
    "DepartmentCalendarAssignmentORM",
    "EmployeeCalendarAssignmentORM",
    "PlatformCalendarORM",
    "ShiftPatternDayORM",
    "ShiftPatternORM",
    "SiteCalendarAssignmentORM",
]
