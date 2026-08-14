from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
    TaskSelectorOptionViewModel,
)

from .detail_builder import build_detail_view_model
from .filtering import (
    build_empty_state,
    build_task_filter_options,
    normalize_workspace_filters,
)
from .overview_builder import build_overview
from .selection import resolve_project_id, resolve_task_id
from .task_mapper import to_task_record_view_model


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
    sort_key: str = "wbsCode",
    sort_direction: str = "asc",
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
    task_page = desktop_api.list_task_page(
        project_id=resolved_project_id or None,
        search_text=filters.search_text,
        status=filters.status_filter,
        priority=filters.priority_filter,
        schedule=filters.schedule_filter,
        page=page,
        page_size=page_size,
        sort_key=sort_key,
        sort_direction=sort_direction,
    )
    resolved_task_id = resolve_task_id(selected_task_id, task_page.items)
    selected_task = next(
        (task for task in task_page.items if task.id == resolved_task_id),
        None,
    )
    parent_project_id = resolved_project_id or (
        selected_task.project_id if selected_task is not None else ""
    )
    parent_tasks = desktop_api.list_tasks(parent_project_id) if parent_project_id else ()
    return TaskCatalogWorkspaceViewModel(
        overview=build_overview(
            total=task_page.total,
            filtered_total=task_page.filtered_total,
            in_progress=task_page.in_progress,
            blocked=task_page.blocked,
            done=task_page.done,
            overdue=task_page.overdue,
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
        tasks=tuple(to_task_record_view_model(task) for task in task_page.items),
        wbs_parent_options=(
            TaskSelectorOptionViewModel(value="", label="Root task"),
            *(
                TaskSelectorOptionViewModel(
                    value=task.id,
                    label=f"{task.wbs_code}  {task.name}",
                    disabled_for_task_ids=(task.id, *task.ancestor_ids),
                )
                for task in parent_tasks
            ),
        ),
        total_count=task_page.filtered_total,
        page=task_page.page,
        page_size=task_page.page_size,
        sort_key=task_page.sort_key,
        sort_direction=task_page.sort_direction,
        selected_task_id=resolved_task_id,
        selected_task_detail=build_detail_view_model(
            desktop_api,
            selected_task,
            assignment_count=0,
            dependency_count=0,
        ),
        empty_state=build_empty_state(
            project_options=options.project_options,
            total=task_page.total,
            filtered_total=task_page.filtered_total,
            search_text=filters.search_text,
            status_filter=filters.status_filter,
            priority_filter=filters.priority_filter,
            schedule_filter=filters.schedule_filter,
        ),
    )
