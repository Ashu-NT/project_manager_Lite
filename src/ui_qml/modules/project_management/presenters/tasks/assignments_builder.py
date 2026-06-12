from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
    TaskExecutionCollectionViewModel,
    TaskSelectorOptionViewModel,
)

from .assignment_mapper import build_assignment_options, to_assignment_record_view_model
from .overview_builder import build_empty_overview
from .utils import resolve_selected_task


def build_assignments_collection(
    *,
    selected_task,
    assignments,
    assignment_options: tuple[TaskSelectorOptionViewModel, ...],
) -> TaskExecutionCollectionViewModel:
    if selected_task is None:
        return TaskExecutionCollectionViewModel(
            title="Assignments",
            subtitle="Resource coverage and effort capture for the selected task.",
            empty_state="Select a task to review assignments and effort coverage.",
        )
    if assignments:
        return TaskExecutionCollectionViewModel(
            title="Assignments",
            subtitle="Resource allocations and logged effort for this task.",
            items=tuple(
                to_assignment_record_view_model(assignment)
                for assignment in assignments
            ),
        )
    empty_state = (
        "No active project resources are available for the selected task's project."
        if not assignment_options
        else "No assignments are linked to the selected task yet."
    )
    return TaskExecutionCollectionViewModel(
        title="Assignments",
        subtitle="Resource allocations and logged effort for this task.",
        empty_state=empty_state,
    )


def build_task_assignments_state(
    desktop_api,
    *,
    task_id: str,
    project_id: str | None = None,
) -> TaskCatalogWorkspaceViewModel:
    normalized_task_id = (task_id or "").strip()
    if not normalized_task_id:
        return TaskCatalogWorkspaceViewModel(
            overview=build_empty_overview(),
            selected_project_id=project_id or "",
            selected_task_id="",
            assignment_options=(),
            assignments=build_assignments_collection(
                selected_task=None,
                assignments=(),
                assignment_options=(),
            ),
        )
    selected_task = resolve_selected_task(
        desktop_api,
        task_id=normalized_task_id,
        project_id=project_id,
    )
    if selected_task is None:
        return TaskCatalogWorkspaceViewModel(
            overview=build_empty_overview(),
            selected_project_id=project_id or "",
            selected_task_id="",
            assignment_options=(),
            assignments=build_assignments_collection(
                selected_task=None,
                assignments=(),
                assignment_options=(),
            ),
        )
    assignments = desktop_api.list_assignments(normalized_task_id)
    assignment_options = build_assignment_options(
        desktop_api,
        selected_task.project_id or project_id,
    )
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=project_id or "",
        selected_task_id=normalized_task_id,
        assignment_options=assignment_options,
        assignments=build_assignments_collection(
            selected_task=selected_task,
            assignments=assignments,
            assignment_options=assignment_options,
        ),
    )
