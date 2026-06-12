from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
)

from .detail_builder import build_detail_view_model
from .filtering import (
    build_empty_state,
    build_task_filter_options,
    filter_tasks,
    normalize_workspace_filters,
)
from .overview_builder import build_overview
from .pagination import paginate_tasks
from .selection import resolve_project_id, resolve_task_id
from .task_mapper import to_task_record_view_model
from .utils import load_tasks_for_project


def build_workspace_state(
    desktop_api,
    *,
    project_id: str | None = None,
    search_text: str = "",
    status_filter: str = "all",
    priority_filter: str = "all",
    schedule_filter: str = "all",
    selected_task_id: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> TaskCatalogWorkspaceViewModel:
    options = build_task_filter_options(desktop_api)
    resolved_project_id = resolve_project_id(project_id, options.project_options)
    filters = normalize_workspace_filters(
        search_text=search_text,
        status_filter=status_filter,
        priority_filter=priority_filter,
        schedule_filter=schedule_filter,
        status_options=options.status_options,
        priority_options=options.priority_options,
        schedule_options=options.schedule_options,
    )
    all_tasks = load_tasks_for_project(desktop_api, resolved_project_id)
    filtered_tasks = filter_tasks(all_tasks, filters)
    paged_tasks = paginate_tasks(filtered_tasks, page=page, page_size=page_size)
    resolved_task_id = resolve_task_id(selected_task_id, filtered_tasks)
    selected_task = next(
        (task for task in filtered_tasks if task.id == resolved_task_id),
        None,
    )
    return TaskCatalogWorkspaceViewModel(
        overview=build_overview(
            all_tasks=all_tasks,
            filtered_tasks=filtered_tasks,
            collaboration_workspace_snapshot=None,
            collaboration_snapshot=None,
            has_selected_task=bool(resolved_task_id),
        ),
        project_options=options.project_options,
        selected_project_id=resolved_project_id,
        status_options=options.status_options,
        bulk_status_options=options.bulk_status_options,
        priority_options=options.priority_options,
        schedule_options=options.schedule_options,
        selected_status_filter=filters.status_filter,
        selected_priority_filter=filters.priority_filter,
        selected_schedule_filter=filters.schedule_filter,
        search_text=filters.search_text,
        tasks=tuple(to_task_record_view_model(task) for task in paged_tasks.items),
        total_count=paged_tasks.total_count,
        page=paged_tasks.page,
        page_size=paged_tasks.page_size,
        selected_task_id=resolved_task_id,
        selected_task_detail=build_detail_view_model(
            desktop_api,
            selected_task,
            assignment_count=0,
            dependency_count=0,
        ),
        empty_state=build_empty_state(
            project_options=options.project_options,
            all_tasks=all_tasks,
            filtered_tasks=filtered_tasks,
            search_text=filters.search_text,
            status_filter=filters.status_filter,
            priority_filter=filters.priority_filter,
            schedule_filter=filters.schedule_filter,
        ),
    )
