from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskRecordViewModel,
    TaskSelectorOptionViewModel,
)


def to_dependency_record_view_model(dependency) -> TaskRecordViewModel:
    lag_label = f"{int(dependency.lag_days):+d}d"
    state = {
        "dependencyId": dependency.id,
        "linkedTaskId": dependency.linked_task_id,
        "linkedTaskName": dependency.linked_task_name,
        "direction": dependency.direction,
        "directionLabel": dependency.direction_label,
        "dependencyType": dependency.dependency_type,
        "dependencyTypeLabel": dependency.dependency_type_label,
        "lagDays": str(int(dependency.lag_days)),
        "relationshipLabel": dependency.relationship_label,
    }
    return TaskRecordViewModel(
        id=dependency.id,
        title=dependency.linked_task_name,
        status_label=dependency.direction_label,
        subtitle=f"{dependency.dependency_type_label} | Lag {lag_label}",
        supporting_text=dependency.relationship_label,
        meta_text=f"Linked task ID: {dependency.linked_task_id}",
        can_primary_action=False,
        can_secondary_action=False,
        state=state,
    )


def build_dependency_type_options(
    desktop_api,
) -> tuple[TaskSelectorOptionViewModel, ...]:
    return tuple(
        TaskSelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_dependency_types()
    )


def build_dependency_task_options(
    all_tasks,
    *,
    selected_task_id: str,
) -> tuple[TaskSelectorOptionViewModel, ...]:
    return tuple(
        TaskSelectorOptionViewModel(value=task.id, label=task.name)
        for task in all_tasks
        if task.id != selected_task_id
    )
