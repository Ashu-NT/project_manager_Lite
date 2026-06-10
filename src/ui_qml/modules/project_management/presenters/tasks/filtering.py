from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskSelectorOptionViewModel,
)

from .task_filters import (
    build_task_priority_options,
    build_task_schedule_options,
    matches_task_filters,
    normalize_task_filter,
)
from .utils import NormalizedTaskFilters, TaskFilterOptions


def build_task_filter_options(desktop_api) -> TaskFilterOptions:
    project_options = (
        TaskSelectorOptionViewModel(value="", label="All Projects"),
        *(
            TaskSelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_projects()
        ),
    )
    raw_status_options = tuple(desktop_api.list_statuses())
    status_options = (
        TaskSelectorOptionViewModel(value="all", label="All statuses"),
        *(
            TaskSelectorOptionViewModel(value=option.value, label=option.label)
            for option in raw_status_options
        ),
    )
    bulk_status_options = tuple(
        TaskSelectorOptionViewModel(value=option.value, label=option.label)
        for option in raw_status_options
    )
    return TaskFilterOptions(
        project_options=project_options,
        status_options=status_options,
        bulk_status_options=bulk_status_options,
        priority_options=build_task_priority_options(),
        schedule_options=build_task_schedule_options(),
    )


def normalize_status_filter(
    status_filter: str,
    status_options: tuple[TaskSelectorOptionViewModel, ...],
) -> str:
    normalized_value = (status_filter or "all").strip().lower()
    available_values = {
        option.value.lower(): option.value
        for option in status_options
    }
    return available_values.get(normalized_value, "all")


def normalize_workspace_filters(
    *,
    search_text: str,
    status_filter: str,
    priority_filter: str,
    schedule_filter: str,
    status_options: tuple[TaskSelectorOptionViewModel, ...],
    priority_options: tuple[TaskSelectorOptionViewModel, ...],
    schedule_options: tuple[TaskSelectorOptionViewModel, ...],
) -> NormalizedTaskFilters:
    return NormalizedTaskFilters(
        search_text=(search_text or "").strip(),
        status_filter=normalize_status_filter(status_filter, status_options),
        priority_filter=normalize_task_filter(priority_filter, priority_options),
        schedule_filter=normalize_task_filter(schedule_filter, schedule_options),
    )


def filter_tasks(all_tasks, filters: NormalizedTaskFilters):
    return tuple(
        task
        for task in all_tasks
        if matches_task_filters(
            task,
            search_text=filters.search_text,
            status_filter=filters.status_filter,
            priority_filter=filters.priority_filter,
            schedule_filter=filters.schedule_filter,
        )
    )


def build_empty_state(
    *,
    project_options,
    all_tasks,
    filtered_tasks,
    search_text: str,
    status_filter: str,
    priority_filter: str,
    schedule_filter: str,
) -> str:
    if not project_options:
        return "No projects are available yet. Create a project before planning tasks."
    if filtered_tasks:
        return ""
    if not all_tasks:
        return "No tasks are available for the selected project yet."
    if (
        search_text
        or status_filter != "all"
        or priority_filter != "all"
        or schedule_filter != "all"
    ):
        return "No tasks match the current filters."
    return "No tasks are available for the selected project yet."
