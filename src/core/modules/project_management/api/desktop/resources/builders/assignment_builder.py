from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.serializers.assignment_serializer import (
    serialize_resource_assignment,
)


def build_resource_assignments(
    resource_id: str,
    *,
    assignment_repo: object | None,
    availability_service: object | None,
    task_service: object | None,
    project_service: object | None,
) -> tuple:
    normalized_id = str(resource_id or "").strip()
    if not normalized_id:
        return ()

    repo = assignment_repo
    if repo is None and availability_service is not None:
        repo = getattr(availability_service, "_assignments", None)
    if repo is None:
        return ()

    list_by_resource = getattr(repo, "list_by_resource", None)
    if not callable(list_by_resource):
        return ()
    try:
        assignments = list(list_by_resource(normalized_id))
    except Exception:
        return ()
    if not assignments:
        return ()

    tasks_by_id: dict[str, object] = {}
    if task_service is not None:
        list_tasks_for_resource = getattr(task_service, "list_tasks_for_resource", None)
        if callable(list_tasks_for_resource):
            try:
                for task in list_tasks_for_resource(normalized_id):
                    tasks_by_id[str(getattr(task, "id", "") or "")] = task
            except Exception:
                pass

    project_names: dict[str, str] = {}
    if project_service is not None:
        get_project = getattr(project_service, "get_project", None)
        for task in tasks_by_id.values():
            project_id = str(getattr(task, "project_id", "") or "")
            if project_id and project_id not in project_names and callable(get_project):
                try:
                    project = get_project(project_id)
                    if project:
                        project_names[project_id] = str(
                            getattr(project, "name", "") or project_id
                        )
                except Exception:
                    project_names[project_id] = project_id

    results = []
    for assignment in assignments:
        task_id = str(getattr(assignment, "task_id", "") or "")
        task = tasks_by_id.get(task_id)
        task_name = str(getattr(task, "name", "") or task_id) if task else task_id
        project_id = str(getattr(task, "project_id", "") or "") if task else ""
        project_name = project_names.get(project_id, project_id)
        results.append(
            serialize_resource_assignment(
                assignment,
                task_id=task_id,
                task_name=task_name,
                project_id=project_id,
                project_name=project_name,
            )
        )
    return tuple(results)


__all__ = ["build_resource_assignments"]
