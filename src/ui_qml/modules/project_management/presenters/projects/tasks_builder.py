from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks import (
    ProjectManagementTasksDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogWorkspaceViewModel,
    ProjectRecordViewModel,
    ProjectSectionCollectionViewModel,
)

from .formatting import format_date_label
from .overview_builder import build_empty_overview


def build_project_tasks_state(
    tasks_desktop_api: ProjectManagementTasksDesktopApi,
    *,
    project_id: str,
) -> ProjectCatalogWorkspaceViewModel:
    normalized_project_id = (project_id or "").strip()
    tasks = (
        tasks_desktop_api.list_tasks(normalized_project_id) if normalized_project_id else ()
    )
    items = tuple(
        ProjectRecordViewModel(
            id=task.id,
            title=task.name,
            status_label=task.status_label,
            subtitle=f"{task.percent_complete:.0f}% complete",
            supporting_text=(
                f"{format_date_label(task.start_date)} → "
                f"{format_date_label(task.end_date)}"
            ),
            meta_text=task.description or "",
        )
        for task in tasks
    )
    return ProjectCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=normalized_project_id,
        project_tasks=ProjectSectionCollectionViewModel(
            title="Tasks",
            subtitle=f"{len(items)} task(s) in this project." if items else "Tasks linked to this project.",
            empty_state="No tasks have been added to this project yet.",
            items=items,
        ),
    )
