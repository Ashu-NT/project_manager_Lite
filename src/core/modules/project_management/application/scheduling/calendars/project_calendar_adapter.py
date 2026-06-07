"""PM-side adapter for the Platform enterprise calendar engine.

PM scheduling uses this instead of calling WorkCalendarEngine directly.
All calendar logic stays in Platform — PM only consumes.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from src.core.platform.calendar.application.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
    ResolvedCalendarContext,
)
from src.core.platform.calendar.application.calendar_assignment_service import (
    CalendarAssignmentService,
)


logger = logging.getLogger(__name__)


class BoundProjectCalendar:
    """
    A WorkCalendarEngine-compatible shim for a specific project.

    Wraps ProjectCalendarAdapter so the SchedulingEngine can call
    is_working_day(date) / add_working_days(date, n) / working_days_between(start, end)
    without needing to know the project_id at every call site.
    """

    def __init__(self, adapter: "ProjectCalendarAdapter", project_id: str) -> None:
        self._adapter = adapter
        self._project_id = project_id

    def is_working_day(self, target_date: date) -> bool:
        return self._adapter.is_working_day(self._project_id, target_date)

    def next_working_day(self, target_date: date, include_today: bool = True) -> date:
        return self._adapter.next_working_day(
            self._project_id, target_date, include_today=include_today
        )

    def add_working_days(self, start: date, working_days: int) -> date:
        return self._adapter.add_working_days(self._project_id, start, working_days)

    def working_days_between(self, start: date, end: date) -> int:
        return self._adapter.working_days_between(self._project_id, start, end)


class ProjectCalendarAdapter:
    """
    Wraps EnterpriseCalendarResolver for a project scope.
    Provides the same date-arithmetic interface as WorkCalendarEngine
    so the scheduling engine can swap in without behavioral changes.
    """

    def __init__(
        self,
        resolver: EnterpriseCalendarResolver,
        assignment_service: CalendarAssignmentService,
    ) -> None:
        self._resolver = resolver
        self._assignment_service = assignment_service

    def _get_site_id_for_project(self, project_id: str) -> Optional[str]:
        return None

    def get_context(
        self, project_id: str, target_date: date
    ) -> ResolvedCalendarContext:
        return self._resolver.resolve_calendar_context(
            project_id=project_id,
            target_date=target_date,
        )

    def is_working_day(self, project_id: str, target_date: date) -> bool:
        ctx = self.get_context(project_id, target_date)
        return ctx.available_hours > 0

    def working_days_between(self, project_id: str, start: date, end: date) -> int:
        if end < start:
            return 0
        # Use resolve_range for bulk efficiency — single set of DB queries for the range
        try:
            days = self._resolver.resolve_range(project_id=project_id, start=start, end=end)
            return sum(1 for d in days if d.available_hours > 0)
        except Exception:
            # Fallback: day-by-day (safe but slower)
            count = 0
            current = start
            while current <= end:
                if self.is_working_day(project_id, current):
                    count += 1
                current += timedelta(days=1)
            return count

    def add_working_days(self, project_id: str, start: date, n: int) -> date:
        if n == 0:
            return start
        # Small moves should fail fast if the calendar is misconfigured. Large
        # moves are still capped so bad data cannot scan decades indefinitely.
        max_iter = min(max(abs(n) * 7, 730), 365 * 40)
        if n > 0:
            current = self.next_working_day(project_id, start, include_today=True)
            remaining = n - 1
            iterations = 0
            while remaining > 0 and iterations < max_iter:
                current += timedelta(days=1)
                if self.is_working_day(project_id, current):
                    remaining -= 1
                iterations += 1
            if remaining > 0:
                logger.warning(
                    "Project calendar add_working_days exhausted search project_id=%s start=%s working_days=%s remaining=%s iterations=%s",
                    project_id,
                    start,
                    n,
                    remaining,
                    iterations,
                )
            return current

        # negative: walk backwards
        remaining = -n
        current = start
        iterations = 0
        while remaining > 0 and iterations < max_iter:
            current -= timedelta(days=1)
            if self.is_working_day(project_id, current):
                remaining -= 1
            iterations += 1
        if remaining > 0:
            logger.warning(
                "Project calendar add_working_days exhausted reverse search project_id=%s start=%s working_days=%s remaining=%s iterations=%s",
                project_id,
                start,
                n,
                remaining,
                iterations,
            )
        return current

    def next_working_day(
        self, project_id: str, target_date: date, *, include_today: bool = True
    ) -> date:
        current = target_date
        if not include_today:
            current += timedelta(days=1)
        # Safety bound: 730 days (2 years) — if no working day found, return best guess
        for _ in range(730):
            if self.is_working_day(project_id, current):
                return current
            current += timedelta(days=1)
        return current  # fallback: return last attempted date

    def get_source_chain(self, project_id: str) -> list[str]:
        return self._resolver.get_source_chain(project_id=project_id)

    def bind_for_project(self, project_id: str) -> Optional["BoundProjectCalendar"]:
        """
        Always returns a BoundProjectCalendar so the SchedulingEngine uses the enterprise
        calendar hierarchy for every project.

        The resolver itself handles the fallback chain: if no project-level calendar is
        assigned it resolves Global → Site → Department in order. A project with no
        assignment still inherits the Global enterprise calendar — the old WorkCalendarEngine
        is not needed and is not consulted.

        Returns None only if the resolver itself is unavailable (e.g. empty bootstrap),
        letting the engine fall back to WorkCalendarEngine as a last resort.
        """
        try:
            # Verify the enterprise system has at least a global calendar before binding.
            # If the resolver has no chains at all (not bootstrapped), return None so
            # the engine falls back to WorkCalendarEngine gracefully.
            chain = self._resolver.get_source_chain(project_id=project_id)
            if not chain:
                return None
            return BoundProjectCalendar(self, project_id)
        except Exception:
            return None


__all__ = ["BoundProjectCalendar", "ProjectCalendarAdapter"]
