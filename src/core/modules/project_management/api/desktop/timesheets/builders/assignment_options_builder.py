from __future__ import annotations

from src.core.modules.project_management.api.desktop.timesheets.models.options import (
    TimesheetAssignmentOptionDescriptor,
)


def build_assignment_options(
    *,
    project_id: str | None = None,
    task_service=None,
) -> tuple[TimesheetAssignmentOptionDescriptor, ...]:
    if task_service is None:
        return ()
    options = [
        TimesheetAssignmentOptionDescriptor(
            value=row.assignment_id,
            label=f"{row.project_name} | {row.task_name} | {row.resource_name}",
            project_id=row.project_id,
            project_name=row.project_name,
            task_id=row.task_id,
            task_name=row.task_name,
            resource_id=row.resource_id,
            resource_name=row.resource_name,
        )
        for row in task_service.list_timesheet_assignment_contexts(
            project_id=project_id
        )
    ]
    options.sort(key=lambda option: option.label.casefold())
    return tuple(options)


__all__ = ["build_assignment_options"]
