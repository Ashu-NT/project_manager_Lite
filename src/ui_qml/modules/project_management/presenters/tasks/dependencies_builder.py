from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
    TaskExecutionCollectionViewModel,
)

from .dependency_mapper import (
    build_dependency_task_options,
    build_dependency_type_options,
    to_dependency_record_view_model,
)
from .overview_builder import build_empty_overview
from .utils import load_tasks_for_project, resolve_selected_task


def build_dependencies_collection(
    *,
    selected_task,
    all_tasks,
    dependencies,
) -> TaskExecutionCollectionViewModel:
    if selected_task is None:
        return TaskExecutionCollectionViewModel(
            title="Dependencies",
            subtitle="Predecessor and successor links for the selected task.",
            empty_state="Select a task to review predecessor and successor links.",
        )
    if dependencies:
        return TaskExecutionCollectionViewModel(
            title="Dependencies",
            subtitle="Sequencing links and lag settings for this task.",
            items=tuple(
                to_dependency_record_view_model(dependency)
                for dependency in dependencies
            ),
        )
    empty_state = (
        "At least two project tasks are required to create a dependency."
        if len(all_tasks) <= 1
        else "No dependencies are linked to the selected task yet."
    )
    return TaskExecutionCollectionViewModel(
        title="Dependencies",
        subtitle="Sequencing links and lag settings for this task.",
        empty_state=empty_state,
    )


def build_task_dependencies_state(
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
            dependency_task_options=(),
            dependency_type_options=(),
            dependencies=build_dependencies_collection(
                selected_task=None,
                all_tasks=(),
                dependencies=(),
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
            dependency_task_options=(),
            dependency_type_options=(),
            dependencies=build_dependencies_collection(
                selected_task=None,
                all_tasks=(),
                dependencies=(),
            ),
        )
    dependencies = desktop_api.list_dependencies(normalized_task_id)
    all_tasks = load_tasks_for_project(desktop_api, selected_task.project_id)
    dependency_type_options = build_dependency_type_options(desktop_api)
    dependency_task_options = build_dependency_task_options(
        all_tasks,
        selected_task_id=normalized_task_id,
    )
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=project_id or "",
        selected_task_id=normalized_task_id,
        dependency_task_options=dependency_task_options,
        dependency_type_options=dependency_type_options,
        dependencies=build_dependencies_collection(
            selected_task=selected_task,
            all_tasks=all_tasks,
            dependencies=dependencies,
        ),
    )
