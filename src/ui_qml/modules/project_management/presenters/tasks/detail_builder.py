from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
    TaskDetailFieldViewModel,
    TaskDetailViewModel,
)

from .overview_builder import build_empty_overview
from .task_mapper import build_task_state
from .task_lookup import resolve_selected_task

def build_detail_view_model(
    desktop_api: Any,
    task: Any,
    *,
    assignment_count: int,
    dependency_count: int,
) -> TaskDetailViewModel:
    if task is None:
        return TaskDetailViewModel(
            title="No task selected",
            empty_state=(
                "Select a task from the catalog to review details or "
                "update progress."
            ),
        )
    state = build_task_state(task)
    return TaskDetailViewModel(
        id=task.id,
        title=task.name,
        status_label=task.status_label,
        subtitle=task.project_name or "Project task",
        description=task.description or "No task description has been added yet.",
        fields=(
            TaskDetailFieldViewModel(
                label="WBS",
                value=state["wbsCode"],
                supporting_text=(
                    f"Summary task with {state['childCount']} direct child task(s)."
                    if state["isSummary"]
                    else "Schedulable execution leaf."
                ),
            ),
            TaskDetailFieldViewModel(label="Start", value=state["startDateLabel"]),
            TaskDetailFieldViewModel(label="Finish", value=state["endDateLabel"]),
            TaskDetailFieldViewModel(label="Duration", value=state["durationLabel"]),
            TaskDetailFieldViewModel(label="Deadline", value=state["deadlineLabel"]),
            TaskDetailFieldViewModel(
                label="Progress",
                value=state["percentCompleteLabel"],
                supporting_text=f"Priority: {state['priorityLabel']}",
            ),
            TaskDetailFieldViewModel(
                label="Actuals",
                value=state["actualStartLabel"],
                supporting_text=f"Actual end: {state['actualEndLabel']}",
            ),
            TaskDetailFieldViewModel(
                label="Assignments",
                value=str(assignment_count),
                supporting_text="Resource allocations linked to this task.",
            ),
            TaskDetailFieldViewModel(
                label="Dependencies",
                value=str(dependency_count),
                supporting_text="Predecessor and successor links in the plan.",
            ),
            TaskDetailFieldViewModel(label="Version", value=str(state["version"])),
        ),
        state=state,
    )

def build_empty_task_detail_state(
    desktop_api: Any,
    *,
    project_id: str | None,
) -> TaskCatalogWorkspaceViewModel:
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=project_id or "",
        selected_task_id="",
        selected_task_detail=build_detail_view_model(
            desktop_api,
            None,
            assignment_count=0,
            dependency_count=0,
        ),
    )

def build_task_basic_detail_state(
    desktop_api: Any,
    *,
    task_id: str,
    project_id: str | None = None,
) -> TaskCatalogWorkspaceViewModel:
    normalized_task_id = (task_id or "").strip()
    selected_task = resolve_selected_task(
        desktop_api,
        task_id=normalized_task_id,
        project_id=project_id,
    )
    if selected_task is None:
        return build_empty_task_detail_state(desktop_api, project_id=project_id)
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=project_id or "",
        selected_task_id=normalized_task_id,
        selected_task_detail=build_detail_view_model(
            desktop_api,
            selected_task,
            assignment_count=0,
            dependency_count=0,
        ),
    )

def build_task_detail_state(
    desktop_api: Any,
    *,
    task_id: str,
    project_id: str | None = None,
) -> TaskCatalogWorkspaceViewModel:
    normalized_task_id = (task_id or "").strip()
    selected_task = resolve_selected_task(
        desktop_api,
        task_id=normalized_task_id,
        project_id=project_id,
    )
    if selected_task is None:
        return build_empty_task_detail_state(desktop_api, project_id=project_id)
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=project_id or "",
        selected_task_id=normalized_task_id,
        selected_task_detail=build_detail_view_model(
            desktop_api,
            selected_task,
            assignment_count=0,
            dependency_count=0,
        ),
    )
