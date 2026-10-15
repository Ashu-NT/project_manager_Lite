"""Calendar working rules inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class WorkingRuleSaveCommand:
    calendar_id: str
    weekday: int
    is_working_day: bool = True
    start_time: time | str | None = None
    end_time: time | str | None = None
    break_start_time: time | str | None = None
    break_end_time: time | str | None = None
    break_minutes: int = 0
    hours_override: float | None = None
    shift_code: str = ""
    effective_from: date | None = None
    effective_to: date | None = None
    priority: int = 0
    commit: bool = True
