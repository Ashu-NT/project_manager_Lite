"""Structural boundary for an external module's project/resource calendar
assignment store (currently satisfied by Project Management's own
SqlAlchemyProjectCalendarAssignmentRepository/
SqlAlchemyResourceCalendarAssignmentRepository).

Platform owns the calendar engine; a consuming module owns its own
project/resource assignment rows (a PM scheduling concept, not a Platform
one) and injects a repository satisfying this Protocol into
CalendarAssignmentService/PlatformCalendarResolver. Platform never imports
the consuming module's concrete domain/repository types -- it only ever
constructs an assignment via the repository's own `create()` factory and
treats the result opaquely (reading only `calendar_id`), so the dependency
points one way: consumer -> Platform, never Platform -> consumer.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable


@runtime_checkable
class ExternalCalendarAssignment(Protocol):
    id: str
    calendar_id: str


class ProjectCalendarAssignmentPort(Protocol):
    def get(
        self, project_id: str, *, at_date: date | None = None
    ) -> ExternalCalendarAssignment | None: ...

    def create(
        self,
        *,
        project_id: str,
        calendar_id: str,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> ExternalCalendarAssignment: ...

    def save(self, assignment: ExternalCalendarAssignment) -> None: ...

    def delete(self, assignment_id: str) -> None: ...

    def list_for_calendar(self, calendar_id: str) -> list[ExternalCalendarAssignment]: ...


class ResourceCalendarAssignmentPort(Protocol):
    def get(
        self, resource_id: str, *, at_date: date | None = None
    ) -> ExternalCalendarAssignment | None: ...

    def create(
        self,
        *,
        resource_id: str,
        calendar_id: str,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> ExternalCalendarAssignment: ...

    def save(self, assignment: ExternalCalendarAssignment) -> None: ...

    def delete(self, assignment_id: str) -> None: ...

    def list_for_calendar(self, calendar_id: str) -> list[ExternalCalendarAssignment]: ...


__all__ = [
    "ExternalCalendarAssignment",
    "ProjectCalendarAssignmentPort",
    "ResourceCalendarAssignmentPort",
]
