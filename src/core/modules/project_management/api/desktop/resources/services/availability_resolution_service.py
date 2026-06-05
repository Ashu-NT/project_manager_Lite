from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from src.core.modules.project_management.application.resources import (
    ResourceAvailabilityService,
    ResourceService,
)
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
)


def resolve_availability_service(
    *,
    availability_service: ResourceAvailabilityService | None,
    resource_service: ResourceService | None,
    task_service: object | None,
    assignment_repo: AssignmentRepository | None,
    work_calendar_engine: CalendarProtocol | None,
) -> ResourceAvailabilityService | None:
    if availability_service is not None:
        return availability_service
    resource_repo = (
        getattr(resource_service, "_resource_repo", None)
        or getattr(task_service, "_resource_repo", None)
    )
    task_repo = getattr(task_service, "_task_repo", None)
    calendar = (
        work_calendar_engine
        or getattr(task_service, "_work_calendar_engine", None)
        or getattr(task_service, "_calendar", None)
    )
    if assignment_repo and resource_repo and task_repo and calendar:
        return ResourceAvailabilityService(
            resource_repo=resource_repo,
            assignment_repo=assignment_repo,
            task_repo=task_repo,
            calendar=calendar,
        )
    return None


__all__ = ["resolve_availability_service"]
