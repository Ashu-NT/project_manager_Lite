from __future__ import annotations

from typing import Any


def load_tasks_for_project(
    desktop_api: Any, project_id: str | None
) -> tuple[Any, ...]:
    normalized_project_id = (project_id or "").strip()
    if not normalized_project_id:
        return ()
    return tuple(desktop_api.list_tasks(normalized_project_id))


def find_task(tasks: Any, task_id: str | None) -> Any:
    normalized_task_id = (task_id or "").strip()
    if not normalized_task_id:
        return None
    return next(
        (task for task in tasks if task.id == normalized_task_id),
        None,
    )


def resolve_selected_task(
    desktop_api: Any,
    *,
    task_id: str,
    project_id: str | None = None,
) -> Any:
    normalized_task_id = (task_id or "").strip()
    if not normalized_task_id:
        return None
    normalized_project_id = (project_id or "").strip()
    if normalized_project_id:
        try:
            selected_task = find_task(
                load_tasks_for_project(desktop_api, normalized_project_id),
                normalized_task_id,
            )
        except Exception:
            selected_task = None
        if selected_task is not None:
            return selected_task
    return desktop_api.get_task(normalized_task_id)


__all__ = ["find_task", "load_tasks_for_project", "resolve_selected_task"]
