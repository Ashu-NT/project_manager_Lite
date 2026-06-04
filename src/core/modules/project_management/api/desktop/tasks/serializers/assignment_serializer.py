from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.assignment import (
    TaskAssignmentDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.services.resource_lookup_service import (
    resource_name_for_assignment,
)


def serialize_assignment(
    assignment,
    *,
    resources_by_id: dict[str, object],
) -> TaskAssignmentDesktopDto:
    return TaskAssignmentDesktopDto(
        id=assignment.id,
        task_id=assignment.task_id,
        resource_id=assignment.resource_id,
        resource_name=resource_name_for_assignment(
            assignment,
            resources_by_id=resources_by_id,
        ),
        allocation_percent=float(getattr(assignment, "allocation_percent", 0.0) or 0.0),
        hours_logged=float(getattr(assignment, "hours_logged", 0.0) or 0.0),
        project_resource_id=getattr(assignment, "project_resource_id", None),
    )


__all__ = ["serialize_assignment"]
