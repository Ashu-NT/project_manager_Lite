from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.options import (
    TaskProjectOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.tasks.services.access_resolution_service import (
    project_rows_for_task_scope,
)


def build_project_options(
    *,
    project_service: object | None,
    task_service: object | None,
) -> tuple[TaskProjectOptionDescriptor, ...]:
    projects = project_rows_for_task_scope(
        project_service=project_service,
        task_service=task_service,
    )
    return tuple(
        TaskProjectOptionDescriptor(value=project.id, label=project.name)
        for project in projects
    )


__all__ = ["build_project_options"]
