from __future__ import annotations

from dataclasses import dataclass


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
