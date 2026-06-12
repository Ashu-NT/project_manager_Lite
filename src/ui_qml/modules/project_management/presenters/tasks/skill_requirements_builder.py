from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
    TaskExecutionCollectionViewModel,
)

from .overview_builder import build_empty_overview
from .skill_requirement_mapper import to_skill_requirement_record_view_model


def build_skill_requirements_collection(
    task_id: str | None,
    requirements,
) -> TaskExecutionCollectionViewModel:
    if task_id is None:
        return TaskExecutionCollectionViewModel(
            title="Skill Requirements",
            subtitle=(
                "Skills and certifications required to assign resources to this task."
            ),
            empty_state=(
                "Select a task to review skill and certification requirements."
            ),
        )
    if requirements:
        return TaskExecutionCollectionViewModel(
            title="Skill Requirements",
            subtitle="Skills and certifications required for resource assignment.",
            items=tuple(
                to_skill_requirement_record_view_model(req)
                for req in requirements
            ),
        )
    return TaskExecutionCollectionViewModel(
        title="Skill Requirements",
        subtitle="Skills and certifications required for resource assignment.",
        empty_state=(
            "No skill or certification requirements are linked to this task."
        ),
    )


def build_task_skill_requirements_state(
    desktop_api,
    *,
    task_id: str,
) -> TaskCatalogWorkspaceViewModel:
    normalized_task_id = (task_id or "").strip()
    if not normalized_task_id:
        return TaskCatalogWorkspaceViewModel(
            overview=build_empty_overview(),
            task_skill_requirements=build_skill_requirements_collection(None, ()),
        )
    reqs = desktop_api.list_task_skill_requirements(normalized_task_id)
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_task_id=normalized_task_id,
        task_skill_requirements=build_skill_requirements_collection(
            normalized_task_id, reqs
        ),
    )
