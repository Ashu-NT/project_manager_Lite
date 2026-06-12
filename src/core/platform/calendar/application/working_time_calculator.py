"""Working time calculator — derives available hours from calendar rules.

All computation is pure (no DB access). Input comes from the resolver.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time

from src.core.platform.calendar.domain.enterprise_calendar import (
    CalendarException,
    CalendarRecurringEvent,
    CalendarWorkingRule,
    ImpactType,
)


def _minutes_between(t1: time, t2: time) -> int:
    return (t2.hour * 60 + t2.minute) - (t1.hour * 60 + t1.minute)


def _event_occurs_on(event: CalendarRecurringEvent, target_date: date) -> bool:
    """Check whether a recurring event fires on target_date using dateutil.rrule."""
    if target_date < event.effective_from:
        return False
    if event.effective_to is not None and target_date > event.effective_to:
        return False
    try:
        from datetime import datetime
        from dateutil.rrule import rrulestr

        dtstart = datetime.combine(event.effective_from, event.start_time)
        rule = rrulestr(event.recurrence_rule, dtstart=dtstart, ignoretz=True)
        day_start = datetime.combine(target_date, time(0, 0))
        day_end = datetime.combine(target_date, time(23, 59, 59))
        occurrences = list(rule.between(day_start, day_end, inc=True))
        return len(occurrences) > 0
    except Exception:
        return False


@dataclass
class DayCapacity:
    date: date
    is_working: bool
    base_hours: float
    available_hours: float
    assigned_hours: float = 0.0
    effective_start: time | None = None
    effective_end: time | None = None
    active_overrides: list[str] = field(default_factory=list)

    @property
    def remaining_hours(self) -> float:
        return max(0.0, self.available_hours - self.assigned_hours)

    @property
    def capacity_percent(self) -> float:
        if self.base_hours <= 0:
            return 0.0
        return round(self.available_hours / self.base_hours * 100, 2)

    @property
    def utilization_percent(self) -> float:
        if self.available_hours <= 0:
            return 0.0
        return round(self.assigned_hours / self.available_hours * 100, 2)

    @property
    def status(self) -> str:
        if not self.is_working or self.available_hours <= 0:
            return "UNAVAILABLE"
        if self.assigned_hours >= self.available_hours:
            return "FULLY_ALLOCATED"
        if self.remaining_hours < 1.0:
            return "CONSTRAINED"
        return "AVAILABLE"


class WorkingTimeCalculator:
    """Pure computation layer. Derives capacity from rules + exceptions + events."""

    def compute_day(
        self,
        *,
        working_rules: list[CalendarWorkingRule],
        exceptions: list[CalendarException],
        recurring_events: list[CalendarRecurringEvent],
        target_date: date,
        assigned_hours: float = 0.0,
    ) -> DayCapacity:
        weekday = target_date.weekday()
        rule = next((r for r in working_rules if r.weekday == weekday), None)

        if rule is None or not rule.is_working_day:
            return DayCapacity(
                date=target_date,
                is_working=False,
                base_hours=0.0,
                available_hours=0.0,
                assigned_hours=assigned_hours,
            )

        base_hours = rule.compute_hours()
        effective_start = rule.start_time
        effective_end = rule.end_time
        overrides: list[str] = []

        # --- Apply exceptions (highest priority wins, UNAVAILABLE stops all) ---
        unavailable_hours = 0.0
        extra_hours = 0.0
        is_fully_unavailable = False

        day_exceptions = [e for e in exceptions if e.exception_date == target_date]
        day_exceptions.sort(key=lambda e: e.priority, reverse=True)

        for exc in day_exceptions:
            impact = exc.impact_type
            if impact == ImpactType.UNAVAILABLE:
                is_fully_unavailable = True
                overrides.append(f"EXCEPTION:{exc.exception_type}")
                break
            elif impact == ImpactType.REDUCED_CAPACITY:
                hours = exc.compute_hours() if exc.hours_override is not None else base_hours
                unavailable_hours += hours
                overrides.append(f"EXCEPTION:{exc.exception_type}")
            elif impact == ImpactType.EXTRA_CAPACITY:
                hours = exc.compute_hours()
                extra_hours += hours
                overrides.append(f"EXCEPTION:{exc.exception_type}")
            elif impact == ImpactType.WORKING:
                if exc.start_time and exc.end_time:
                    effective_start = exc.start_time
                    effective_end = exc.end_time
                    overrides.append(f"EXCEPTION:WORKING_OVERRIDE")

        if is_fully_unavailable:
            return DayCapacity(
                date=target_date,
                is_working=False,
                base_hours=base_hours,
                available_hours=0.0,
                assigned_hours=assigned_hours,
                effective_start=effective_start,
                effective_end=effective_end,
                active_overrides=overrides,
            )

        # --- Apply recurring events ---
        for event in recurring_events:
            if not _event_occurs_on(event, target_date):
                continue
            impact = event.impact_type
            duration = event.duration_hours()
            if impact == ImpactType.UNAVAILABLE:
                unavailable_hours += duration
                overrides.append(f"RECURRING:{event.event_type}")
            elif impact == ImpactType.REDUCED_CAPACITY:
                pct = event.capacity_impact_percent
                if pct is not None:
                    unavailable_hours += base_hours * pct / 100.0
                else:
                    unavailable_hours += duration
                overrides.append(f"RECURRING:{event.event_type}")
            elif impact == ImpactType.EXTRA_CAPACITY:
                extra_hours += duration
                overrides.append(f"RECURRING:{event.event_type}")

        available_hours = max(0.0, base_hours - unavailable_hours + extra_hours)

        return DayCapacity(
            date=target_date,
            is_working=available_hours > 0,
            base_hours=base_hours,
            available_hours=round(available_hours, 4),
            assigned_hours=assigned_hours,
            effective_start=effective_start,
            effective_end=effective_end,
            active_overrides=list(dict.fromkeys(overrides)),
        )

    def compute_range(
        self,
        *,
        working_rules: list[CalendarWorkingRule],
        exceptions: list[CalendarException],
        recurring_events: list[CalendarRecurringEvent],
        start: date,
        end: date,
        assigned_hours_by_date: dict[date, float] | None = None,
    ) -> list[DayCapacity]:
        from datetime import timedelta

        results = []
        current = start
        while current <= end:
            ah = (assigned_hours_by_date or {}).get(current, 0.0)
            results.append(
                self.compute_day(
                    working_rules=working_rules,
                    exceptions=exceptions,
                    recurring_events=recurring_events,
                    target_date=current,
                    assigned_hours=ah,
                )
            )
            current += timedelta(days=1)
        return results


__all__ = ["DayCapacity", "WorkingTimeCalculator"]
