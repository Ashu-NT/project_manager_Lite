"""DTOs and commands for the enterprise calendar desktop API."""

from __future__ import annotations

from dataclasses import dataclass

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
    updated_at: str = ""


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
    anchor_date: str = ""


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


# ---------------------------------------------------------------------------
# Resolution DTOs
# ---------------------------------------------------------------------------


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
class EffectiveCalendarDto:
    """Identity result -- which calendar is in effect, and its full source
    chain -- the single read shape for Site/Department/Employee effective-
    calendar summary cards. Distinct from ResolvedContextDto (a capacity/
    hours result for one date)."""

    has_calendar: bool
    calendar_id: str
    calendar_name: str
    timezone: str
    source_chain: list


@dataclass(frozen=True)
class CalendarDayDto:
    """One resolved day, for a visual Month view -- a thin read projection
    over ResolvedCalendarContext (per-day capacity) and its exceptions,
    never a second calculation path. At most one exception is summarized
    per day (the common case); a day with several active exceptions still
    reports the first one for display -- full detail belongs in the
    Exceptions editor, not a Month cell."""

    date: str
    is_working_day: bool
    base_hours: float
    available_hours: float
    status: str
    start_time: str = ""
    end_time: str = ""
    exception_type: str = ""
    exception_name: str = ""
    impact_type: str = ""


@dataclass(frozen=True)
class WorkingDaysResultDto:
    start_date: str
    end_date: str
    working_days: int


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
    "CalendarDayDto",
    "CalendarDto",
    "CalendarExceptionDto",
    "RecurringEventDto",
    "ResolvedContextDto",
    "ResourceCapacityDto",
    "ShiftPatternDayDto",
    "ShiftPatternDto",
    "WorkingDaysResultDto",
    "WorkingRuleDto",
]
