"""Calendar recurring events inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class RecurringEventCreateCommand:
    calendar_id: str
    title: str
    event_type: str
    recurrence_rule: str
    start_time: time | str
    end_time: time | str
    impact_type: str
    effective_from: date | str
    scope_type: str | None = None
    scope_id: str | None = None
    capacity_impact_percent: float | None = None
    effective_to: date | str | None = None
    priority: int = 0


@dataclass(frozen=True)
class RecurringEventUpdateCommand:
    event_id: str
    title: str = ""
    event_type: str = ""
    recurrence_rule: str = ""
    start_time: time | str | None = None
    end_time: time | str | None = None
    impact_type: str = ""
    capacity_impact_percent: float | None = None
    effective_from: date | str | None = None
    effective_to: date | str | None = None
    is_active: bool | None = None
    priority: int | None = None
