from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.dependency import (
    TaskDependencyDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.utils.dependency_utils import (
    dependency_direction,
    dependency_type_label,
)


def serialize_dependency(
    dependency,
    *,
    current_task_id: str,
    tasks_by_id: dict[str, object],
) -> TaskDependencyDesktopDto:
    direction, linked_task_id = dependency_direction(current_task_id, dependency)
    predecessor = tasks_by_id.get(dependency.predecessor_task_id)
    successor = tasks_by_id.get(dependency.successor_task_id)
    predecessor_name = str(
        getattr(predecessor, "name", "") or dependency.predecessor_task_id
    )
    successor_name = str(
        getattr(successor, "name", "") or dependency.successor_task_id
    )
    linked_task_name = str(
        getattr(tasks_by_id.get(linked_task_id), "name", "") or linked_task_id
    )
    return TaskDependencyDesktopDto(
        id=dependency.id,
        direction=direction,
        direction_label="Predecessor" if direction == "PREDECESSOR" else "Successor",
        linked_task_id=linked_task_id,
        linked_task_name=linked_task_name,
        dependency_type=dependency.dependency_type.value,
        dependency_type_label=dependency_type_label(dependency.dependency_type),
        lag_days=int(getattr(dependency, "lag_days", 0) or 0),
        relationship_label=f"{predecessor_name} -> {successor_name}",
    )


__all__ = ["serialize_dependency"]
