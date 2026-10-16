"""Dependency aggregate mapping without dates or relationship-label formatting."""

from src.core.modules.project_management.application.tasks.dto.responses.dependency import (
    TaskDependencyResponseDto,
)
from src.core.modules.project_management.contracts.reads.tasks import (
    TaskDependencyReadItem,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency


def map_dependency(dependency: TaskDependency) -> TaskDependencyResponseDto:
    return TaskDependencyResponseDto(
        id=dependency.id,
        predecessor_task_id=dependency.predecessor_task_id,
        successor_task_id=dependency.successor_task_id,
        dependency_type=dependency.dependency_type,
        lag_days=dependency.lag_days,
        version=int(getattr(dependency, "version", 1)),
    )


def map_dependency_read_item(
    dependency: TaskDependency, *, task_id: str, tasks_by_id: dict[str, Task]
) -> TaskDependencyReadItem:
    is_predecessor = dependency.successor_task_id == task_id
    linked_id = dependency.predecessor_task_id if is_predecessor else dependency.successor_task_id
    linked = tasks_by_id.get(linked_id)
    return TaskDependencyReadItem(
        dependency_id=dependency.id,
        direction="PREDECESSOR" if is_predecessor else "SUCCESSOR",
        linked_task_id=linked_id,
        linked_task_name=linked.name if linked is not None else linked_id,
        linked_task_code=getattr(linked, "code", "") if linked is not None else "",
        linked_task_status=linked.status.value if linked is not None else "",
        linked_task_start=linked.start_date if linked is not None else None,
        linked_task_end=linked.end_date if linked is not None else None,
        dependency_type=dependency.dependency_type.value,
        lag_days=dependency.lag_days,
        version=int(getattr(dependency, "version", 1)),
    )
