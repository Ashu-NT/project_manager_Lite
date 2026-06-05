from __future__ import annotations

from src.core.modules.project_management.api.desktop.timesheets.models.options import (
    TimesheetAssignmentOptionDescriptor,
)


def build_assignment_options(
    *,
    project_id: str | None = None,
    project_service=None,
    task_service=None,
    resource_service=None,
) -> tuple[TimesheetAssignmentOptionDescriptor, ...]:
    if task_service is None or project_service is None:
        return ()
    project_lookup = {
        project.id: project
        for project in project_service.list_projects()
    }
    project_ids = (
        [str(project_id or "").strip()]
        if str(project_id or "").strip()
        else [project.id for project in project_lookup.values()]
    )
    options: list[TimesheetAssignmentOptionDescriptor] = []
    for current_project_id in project_ids:
        if current_project_id not in project_lookup:
            continue
        tasks = task_service.list_tasks_for_project(current_project_id)
        if not tasks:
            continue
        assignments = task_service.list_assignments_for_tasks([task.id for task in tasks])
        task_lookup = {task.id: task for task in tasks}
        for assignment in assignments:
            task = task_lookup.get(assignment.task_id)
            if task is None:
                continue
            resource = (
                resource_service.get_resource(assignment.resource_id)
                if resource_service is not None
                else None
            )
            project = project_lookup[current_project_id]
            resource_name = getattr(resource, "name", assignment.resource_id)
            label = f"{project.name} | {task.name} | {resource_name}"
            options.append(
                TimesheetAssignmentOptionDescriptor(
                    value=assignment.id,
                    label=label,
                    project_id=current_project_id,
                    project_name=project.name,
                    task_id=task.id,
                    task_name=task.name,
                    resource_id=assignment.resource_id,
                    resource_name=resource_name,
                )
            )
    options.sort(key=lambda option: option.label.casefold())
    return tuple(options)


__all__ = ["build_assignment_options"]
