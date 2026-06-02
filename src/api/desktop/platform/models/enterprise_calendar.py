"""DTOs and commands for the enterprise calendar desktop API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional


# ---------------------------------------------------------------------------
# Calendar DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalendarDto:
    id: str
    organization_id: str
    code: str
    name: str
    calendar_type: str
    timezone: str
    is_default: bool
    is_active: bool
    description: str = ""
    base_calendar_id: str = ""
    scope_type: str = ""
    scope_id: str = ""
    locale: str = ""
    effective_from: str = ""
    effective_to: str = ""
    priority: int = 0
    version: int = 1


@dataclass(frozen=True)
class CalendarCreateCommand:
    code: str
    name: str
    calendar_type: str
    timezone: str = "UTC"
    description: str = ""
    base_calendar_id: str = ""
    scope_type: str = ""
    scope_id: str = ""
    locale: str = ""
    is_default: bool = False
    effective_from: str = ""
    effective_to: str = ""
    priority: int = 0


@dataclass(frozen=True)
class CalendarUpdateCommand:
    calendar_id: str
    name: str = ""
    description: str = ""
    timezone: str = ""
    locale: str = ""
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    effective_from: str = ""
    effective_to: str = ""
    priority: Optional[int] = None


# ---------------------------------------------------------------------------
# Working Rule DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkingRuleDto:
    id: str
    calendar_id: str
    weekday: int
    is_working_day: bool
    start_time: str = ""
    end_time: str = ""
    break_start_time: str = ""
    break_end_time: str = ""
    break_minutes: int = 0
    hours_override: float = 0.0
    shift_code: str = ""
    computed_hours: float = 0.0


@dataclass(frozen=True)
class WorkingRuleSaveCommand:
    calendar_id: str
    weekday: int
    is_working_day: bool = True
    start_time: str = ""
    end_time: str = ""
    break_start_time: str = ""
    break_end_time: str = ""
    break_minutes: int = 0
    hours_override: float = 0.0
    shift_code: str = ""


# ---------------------------------------------------------------------------
# Exception DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalendarExceptionDto:
    id: str
    calendar_id: str
    exception_date: str
    exception_type: str
    name: str
    impact_type: str
    approval_status: str
    scope_type: str = ""
    scope_id: str = ""
    description: str = ""
    start_time: str = ""
    end_time: str = ""
    hours_override: float = 0.0
    priority: int = 0
    approved_by: str = ""


@dataclass(frozen=True)
class ExceptionCreateCommand:
    calendar_id: str
    exception_date: str
    exception_type: str
    name: str
    impact_type: str
    scope_type: str = ""
    scope_id: str = ""
    description: str = ""
    start_time: str = ""
    end_time: str = ""
    hours_override: float = 0.0
    priority: int = 0
    approval_status: str = "APPROVED"


@dataclass(frozen=True)
class ExceptionUpdateCommand:
    exception_id: str
    name: str = ""
    description: str = ""
    exception_type: str = ""
    impact_type: str = ""
    hours_override: float = 0.0
    priority: Optional[int] = None
    approval_status: str = ""
    approved_by: str = ""


# ---------------------------------------------------------------------------
# Recurring Event DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecurringEventDto:
    id: str
    calendar_id: str
    title: str
    event_type: str
    recurrence_rule: str
    start_time: str
    end_time: str
    impact_type: str
    effective_from: str
    is_active: bool
    scope_type: str = ""
    scope_id: str = ""
    capacity_impact_percent: float = 0.0
    effective_to: str = ""
    priority: int = 0


@dataclass(frozen=True)
class RecurringEventCreateCommand:
    calendar_id: str
    title: str
    event_type: str
    recurrence_rule: str
    start_time: str
    end_time: str
    impact_type: str
    effective_from: str
    scope_type: str = ""
    scope_id: str = ""
    capacity_impact_percent: float = 0.0
    effective_to: str = ""
    priority: int = 0


@dataclass(frozen=True)
class RecurringEventUpdateCommand:
    event_id: str
    title: str = ""
    event_type: str = ""
    recurrence_rule: str = ""
    start_time: str = ""
    end_time: str = ""
    impact_type: str = ""
    capacity_impact_percent: float = 0.0
    effective_from: str = ""
    effective_to: str = ""
    is_active: Optional[bool] = None
    priority: Optional[int] = None


# ---------------------------------------------------------------------------
# Shift Pattern DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShiftPatternDto:
    id: str
    organization_id: str
    code: str
    name: str
    pattern_type: str
    timezone: str
    is_active: bool
    description: str = ""
    rotation_cycle_days: int = 0


@dataclass(frozen=True)
class ShiftPatternDayDto:
    id: str
    shift_pattern_id: str
    day_offset: int
    is_working_day: bool
    start_time: str = ""
    end_time: str = ""
    break_minutes: int = 0
    hours: float = 0.0
    shift_label: str = ""


@dataclass(frozen=True)
class ShiftPatternCreateCommand:
    code: str
    name: str
    pattern_type: str
    timezone: str = "UTC"
    description: str = ""
    rotation_cycle_days: int = 0


@dataclass(frozen=True)
class ShiftPatternUpdateCommand:
    pattern_id: str
    name: str = ""
    description: str = ""
    pattern_type: str = ""
    timezone: str = ""
    rotation_cycle_days: int = 0
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Assignment DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalendarAssignmentDto:
    id: str
    entity_type: str
    entity_id: str
    calendar_id: str
    calendar_name: str
    calendar_type: str
    is_default: bool
    priority: int = 0
    effective_from: str = ""
    effective_to: str = ""


@dataclass(frozen=True)
class SiteCalendarAssignCommand:
    site_id: str
    calendar_id: str
    effective_from: str = ""
    effective_to: str = ""
    is_default: bool = True
    priority: int = 0


@dataclass(frozen=True)
class DeptCalendarAssignCommand:
    department_id: str
    calendar_id: str
    effective_from: str = ""
    effective_to: str = ""
    is_default: bool = True
    priority: int = 0


@dataclass(frozen=True)
class EmpCalendarAssignCommand:
    employee_id: str
    calendar_id: str
    effective_from: str = ""
    effective_to: str = ""
    is_default: bool = True
    priority: int = 0


@dataclass(frozen=True)
class ProjectCalendarAssignCommand:
    project_id: str
    calendar_id: str
    effective_from: str = ""
    effective_to: str = ""
    is_default: bool = True
    priority: int = 0


@dataclass(frozen=True)
class ResourceCalendarAssignCommand:
    resource_id: str
    calendar_id: str
    effective_from: str = ""
    effective_to: str = ""
    is_default: bool = True
    priority: int = 0


# ---------------------------------------------------------------------------
# Resolution DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolveContextCommand:
    target_date: str
    site_id: str = ""
    department_id: str = ""
    employee_id: str = ""
    project_id: str = ""
    resource_id: str = ""
    worker_type: str = ""
    assigned_hours: float = 0.0


@dataclass(frozen=True)
class ResolvedContextDto:
    date: str
    base_hours: float
    available_hours: float
    assigned_hours: float
    remaining_hours: float
    capacity_percent: float
    utilization_percent: float
    status: str
    source_chain: list
    overrides: list
    timezone: str
    exceptions: list
    working_start: str = ""
    working_end: str = ""


@dataclass(frozen=True)
class WorkingDaysCommand:
    start_date: str
    end_date: str = ""
    working_days: int = 0
    project_id: str = ""
    resource_id: str = ""


@dataclass(frozen=True)
class WorkingDaysResultDto:
    start_date: str
    end_date: str
    working_days: int


@dataclass(frozen=True)
class ResourceCapacityCommand:
    resource_id: str
    start_date: str
    end_date: str
    project_id: str = ""


@dataclass(frozen=True)
class ResourceCapacityDto:
    resource_id: str
    start: str
    end: str
    base_hours: float
    available_hours: float
    assigned_hours: float
    remaining_hours: float
    capacity_percent: float
    utilization_percent: float
    working_days: int
    unavailable_days: int
    conflicts: list
    source_chain: list


__all__ = [
    "CalendarAssignmentDto",
    "CalendarCreateCommand",
    "CalendarDto",
    "CalendarExceptionDto",
    "CalendarUpdateCommand",
    "DeptCalendarAssignCommand",
    "EmpCalendarAssignCommand",
    "ExceptionCreateCommand",
    "ExceptionUpdateCommand",
    "ProjectCalendarAssignCommand",
    "RecurringEventCreateCommand",
    "RecurringEventDto",
    "RecurringEventUpdateCommand",
    "ResolveContextCommand",
    "ResolvedContextDto",
    "ResourceCalendarAssignCommand",
    "ResourceCapacityCommand",
    "ResourceCapacityDto",
    "ShiftPatternCreateCommand",
    "ShiftPatternDayDto",
    "ShiftPatternDto",
    "ShiftPatternUpdateCommand",
    "SiteCalendarAssignCommand",
    "WorkingDaysCommand",
    "WorkingDaysResultDto",
    "WorkingRuleDto",
    "WorkingRuleSaveCommand",
]
