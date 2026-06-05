from __future__ import annotations

from src.core.modules.project_management.api.desktop.timesheets.models.options import (
    TimesheetProjectOptionDescriptor,
)


def build_project_options(
    project_service=None,
) -> tuple[TimesheetProjectOptionDescriptor, ...]:
    if project_service is None:
        return ()
    projects = sorted(
        project_service.list_projects(),
        key=lambda project: (project.name or "").casefold(),
    )
    return tuple(
        TimesheetProjectOptionDescriptor(value=project.id, label=project.name)
        for project in projects
    )


__all__ = ["build_project_options"]
