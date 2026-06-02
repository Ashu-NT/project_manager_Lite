"""PM-side adapter for the Platform enterprise calendar engine.

PM scheduling uses this instead of calling WorkCalendarEngine directly.
All calendar logic stays in Platform — PM only consumes.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from src.core.platform.calendar.application.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
    ResolvedCalendarContext,
)
from src.core.platform.calendar.application.calendar_assignment_service import (
    CalendarAssignmentService,
)


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

        if n > 0:
            current = self.next_working_day(project_id, start, include_today=True)
            remaining = n - 1
            while remaining > 0:
                current += timedelta(days=1)
                if self.is_working_day(project_id, current):
                    remaining -= 1
            return current

        # negative: walk backwards
        remaining = -n
        current = start
        while remaining > 0:
            current -= timedelta(days=1)
            if self.is_working_day(project_id, current):
                remaining -= 1
        return current

    def next_working_day(
        self, project_id: str, target_date: date, *, include_today: bool = True
    ) -> date:
        current = target_date
        if not include_today:
            current += timedelta(days=1)
        while not self.is_working_day(project_id, current):
            current += timedelta(days=1)
        return current

    def get_source_chain(self, project_id: str) -> list[str]:
        return self._resolver.get_source_chain(project_id=project_id)


__all__ = ["ProjectCalendarAdapter"]
