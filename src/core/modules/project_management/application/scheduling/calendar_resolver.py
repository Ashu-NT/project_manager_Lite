from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.core.modules.project_management.application.scheduling.work_calendar_engine import (
    WorkCalendarEngine,
)


@dataclass
class CalendarContext:
    """
    All calendar references needed to resolve priority for a given scheduling scope.

    Priority order (highest → lowest):
        resource > project > site > organization > default
    """
    resource_calendar: Optional[WorkCalendarEngine] = None
    project_calendar: Optional[WorkCalendarEngine] = None
    site_calendar: Optional[WorkCalendarEngine] = None
    organization_calendar: Optional[WorkCalendarEngine] = None
    default_calendar: Optional[WorkCalendarEngine] = None


class CalendarResolver:
    """
    Resolves which WorkCalendarEngine to use for a given scheduling scope.

    Enterprise rule:
        resource calendar  >  project calendar  >  site calendar
        >  organization calendar  >  default calendar

    The resolved calendar is used for working-day arithmetic in CPM calculations,
    leveling, and baseline comparisons.
    """

    def __init__(self, default_calendar: WorkCalendarEngine) -> None:
        self._default = default_calendar

    def resolve(self, context: CalendarContext) -> WorkCalendarEngine:
        """Return the highest-priority non-None calendar from the context."""
        for cal in (
            context.resource_calendar,
            context.project_calendar,
            context.site_calendar,
            context.organization_calendar,
            context.default_calendar,
        ):
            if cal is not None:
                return cal
        return self._default

    def resolve_for_resource(
        self,
        resource_calendar: Optional[WorkCalendarEngine] = None,
        project_calendar: Optional[WorkCalendarEngine] = None,
        site_calendar: Optional[WorkCalendarEngine] = None,
        organization_calendar: Optional[WorkCalendarEngine] = None,
    ) -> WorkCalendarEngine:
        """Convenience helper that builds a CalendarContext and resolves it."""
        ctx = CalendarContext(
            resource_calendar=resource_calendar,
            project_calendar=project_calendar,
            site_calendar=site_calendar,
            organization_calendar=organization_calendar,
            default_calendar=None,
        )
        return self.resolve(ctx)

    def resolve_for_project(
        self,
        project_calendar: Optional[WorkCalendarEngine] = None,
        site_calendar: Optional[WorkCalendarEngine] = None,
        organization_calendar: Optional[WorkCalendarEngine] = None,
    ) -> WorkCalendarEngine:
        """Convenience helper when resource-level override is not needed."""
        ctx = CalendarContext(
            project_calendar=project_calendar,
            site_calendar=site_calendar,
            organization_calendar=organization_calendar,
        )
        return self.resolve(ctx)


__all__ = ["CalendarContext", "CalendarResolver"]
