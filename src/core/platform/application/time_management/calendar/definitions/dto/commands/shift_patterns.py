"""Calendar shift patterns inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class ShiftPatternCreateCommand:
    code: str
    name: str
    pattern_type: str
    timezone: str = "UTC"
    description: str = ""
    rotation_cycle_days: int | None = None
    anchor_date: date | str | None = None


@dataclass(frozen=True)
class ShiftPatternUpdateCommand:
    pattern_id: str
    name: str = ""
    description: str = ""
    pattern_type: str = ""
    timezone: str = ""
    rotation_cycle_days: int | None = None
    anchor_date: date | str | None = None
    is_active: bool | None = None


@dataclass(frozen=True)
class ShiftPatternDaySetCommand:
    pattern_id: str
    day_offset: int
    is_working_day: bool = True
    start_time: time | str | None = None
    end_time: time | str | None = None
    break_minutes: int = 0
    hours: float | None = None
    shift_label: str = ""
