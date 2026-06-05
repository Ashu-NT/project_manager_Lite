from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.models.assignments import (
    ResourceAssignmentDesktopDto,
)


def serialize_resource_assignment(
    assignment,
    *,
    task_id: str,
    task_name: str,
    project_id: str,
    project_name: str,
) -> ResourceAssignmentDesktopDto:
    allocation_percent = float(getattr(assignment, "allocation_percent", 0.0) or 0.0)
    hours_logged = float(getattr(assignment, "hours_logged", 0.0) or 0.0)
    return ResourceAssignmentDesktopDto(
        id=str(getattr(assignment, "id", "") or ""),
        task_id=task_id,
        task_name=task_name,
        project_id=project_id,
        project_name=project_name,
        allocation_percent=allocation_percent,
        hours_logged=hours_logged,
        allocation_label=f"{allocation_percent:.0f}%",
        hours_label=f"{hours_logged:.1f} hrs",
    )


__all__ = ["serialize_resource_assignment"]
