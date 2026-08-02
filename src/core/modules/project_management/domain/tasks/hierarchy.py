"""Read models for the Task-owned work breakdown structure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency


def select_leaf_tasks(tasks: list[Task]) -> list[Task]:
    """Return schedulable execution leaves without mutating aggregate state."""
    summary_ids = {
        task.parent_task_id
        for task in tasks
        if task.parent_task_id is not None
    }
    return [task for task in tasks if task.id not in summary_ids]


def select_leaf_dependencies(
    dependencies: list[TaskDependency],
    leaf_tasks: list[Task],
) -> list[TaskDependency]:
    leaf_ids = {task.id for task in leaf_tasks}
    return [
        dependency
        for dependency in dependencies
        if dependency.predecessor_task_id in leaf_ids
        and dependency.successor_task_id in leaf_ids
    ]


def order_tasks_children_first(tasks: list[Task]) -> list[Task]:
    """Order a valid hierarchy for restrictive child-before-parent deletion."""
    tasks_by_id = {task.id: task for task in tasks}

    def depth(task: Task) -> int:
        current = task
        visited: set[str] = set()
        resolved = 0
        while current.parent_task_id is not None:
            if current.id in visited:
                break
            visited.add(current.id)
            parent = tasks_by_id.get(current.parent_task_id)
            if parent is None:
                break
            resolved += 1
            current = parent
        return resolved

    return sorted(tasks, key=lambda task: (depth(task), task.sort_order, task.id), reverse=True)


@dataclass(frozen=True)
class TaskHierarchyNode:
    task: Task
    depth: int
    is_summary: bool
    child_count: int
    ancestor_ids: tuple[str, ...]


@dataclass(frozen=True)
class TaskHierarchyRollup:
    task_id: str
    descendant_task_ids: tuple[str, ...]
    leaf_task_ids: tuple[str, ...]
    start_date: date | None
    end_date: date | None
    duration_days: int
    percent_complete: float
    status: TaskStatus


__all__ = [
    "TaskHierarchyNode",
    "TaskHierarchyRollup",
    "order_tasks_children_first",
    "select_leaf_dependencies",
    "select_leaf_tasks",
]
