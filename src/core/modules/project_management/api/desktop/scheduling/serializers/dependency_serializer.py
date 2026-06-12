"""Dependency serializers."""

from src.core.modules.project_management.api.desktop.scheduling.models.dependencies import SchedulingDependencyDto
from src.core.modules.project_management.api.desktop.scheduling.formatters.dependency_formatter import dependency_type_label
from src.core.modules.project_management.api.desktop.scheduling.utils.dependency_utils import dependency_direction


def serialize_dependency(dependency, *, current_task_id: str, tasks_by_id: dict) -> SchedulingDependencyDto:
    direction, related_activity_id = dependency_direction(current_task_id, dependency)
    predecessor = tasks_by_id.get(dependency.predecessor_task_id)
    successor = tasks_by_id.get(dependency.successor_task_id)
    predecessor_name = str(getattr(predecessor, "name", "") or dependency.predecessor_task_id)
    successor_name = str(getattr(successor, "name", "") or dependency.successor_task_id)
    related_name = str(getattr(tasks_by_id.get(related_activity_id), "name", "") or related_activity_id)
    return SchedulingDependencyDto(
        id=dependency.id,
        direction=direction,
        direction_label="Predecessor" if direction == "PREDECESSOR" else "Successor",
        related_activity_id=related_activity_id,
        related_activity_name=related_name,
        dependency_type=dependency.dependency_type.value,
        dependency_type_label=dependency_type_label(dependency.dependency_type),
        lag_days=int(getattr(dependency, "lag_days", 0) or 0),
        relationship_label=f"{predecessor_name} -> {successor_name}",
        status_label="Linked",
    )


__all__ = ["serialize_dependency"]
