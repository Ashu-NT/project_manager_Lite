"""CalendarProtocol — structural interface for any calendar engine.

Both GlobalCalendarShim and BoundProjectCalendar satisfy this protocol.
Use this instead of the deleted WorkCalendarEngine as a type annotation.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable


@runtime_checkable
class CalendarProtocol(Protocol):
    def is_working_day(self, target_date: date) -> bool: ...
    def next_working_day(self, target_date: date, include_today: bool = True) -> date: ...
    def add_working_days(self, start: date, working_days: int) -> date: ...
    def working_days_between(self, start: date, end: date) -> int: ...


__all__ = ["CalendarProtocol"]
