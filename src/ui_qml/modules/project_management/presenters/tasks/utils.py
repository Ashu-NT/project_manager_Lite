from __future__ import annotations

from dataclasses import dataclass

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskSelectorOptionViewModel,
)


@dataclass(frozen=True)
class TaskFilterOptions:
    project_options: tuple[TaskSelectorOptionViewModel, ...]
    status_options: tuple[TaskSelectorOptionViewModel, ...]
    bulk_status_options: tuple[TaskSelectorOptionViewModel, ...]
    priority_options: tuple[TaskSelectorOptionViewModel, ...]
    schedule_options: tuple[TaskSelectorOptionViewModel, ...]


@dataclass(frozen=True)
class NormalizedTaskFilters:
    search_text: str
    status_filter: str
    priority_filter: str
    schedule_filter: str


def load_tasks_for_project(desktop_api, project_id: str | None):
    normalized_project_id = (project_id or "").strip()
    if normalized_project_id:
        return desktop_api.list_tasks(normalized_project_id)
    return desktop_api.list_all_tasks()


def find_task(tasks, task_id: str | None):
    normalized_task_id = (task_id or "").strip()
    if not normalized_task_id:
        return None
    return next(
        (task for task in tasks if task.id == normalized_task_id),
        None,
    )


def resolve_selected_task(desktop_api, *, task_id: str, project_id: str | None = None):
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
