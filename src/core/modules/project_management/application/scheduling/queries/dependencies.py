"""Scheduling project-edge query using canonical task dependency responses."""

from src.core.modules.project_management.application.tasks.dto.responses.dependency import (
    TaskDependencyResponseDto,
)
from src.core.modules.project_management.application.tasks.mappers.dependency import (
    map_dependency,
)
from src.core.modules.project_management.application.tasks.queries.dependency_query import (
    TaskDependencyQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)


def query_project_dependencies(
    project_id: str,
    dependency_query: TaskDependencyQueryHandler,
    task_lookup: TaskLookupQueryHandler,
) -> tuple[TaskDependencyResponseDto, ...]:
    tasks = {task.id: task for task in task_lookup.list_tasks_for_project(project_id)}
    dependencies = dependency_query.list_dependencies_for_project(project_id)
    rows = [map_dependency(dependency) for dependency in dependencies]

    def task_name(task_id: str) -> str:
        task = tasks.get(task_id)
        return str(task.name or task_id).casefold() if task is not None else task_id.casefold()

    rows.sort(key=lambda row: (
        task_name(row.predecessor_task_id), task_name(row.successor_task_id), row.dependency_type.value,
    ))
    return tuple(rows)
