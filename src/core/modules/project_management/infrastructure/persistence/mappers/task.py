from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment, TaskDependency
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskAssignmentORM, TaskDependencyORM, TaskORM


def task_to_orm(task: Task) -> TaskORM:
    return TaskORM(
        id=task.id,
        project_id=task.project_id,
        task_code=getattr(task, "code", "") or None,
        parent_task_id=task.parent_task_id,
        wbs_code=task.wbs_code,
        sort_order=task.sort_order,
        name=task.name,
        description=task.description,
        start_date=task.start_date,
        end_date=task.end_date,
        duration_days=task.duration_days,
        status=task.status,
        priority=task.priority,
        percent_complete=task.percent_complete,
        actual_start=task.actual_start,
        actual_end=task.actual_end,
        deadline=task.deadline,
        is_milestone=getattr(task, "is_milestone", False),
        version=getattr(task, "version", 1),
    )


def task_from_orm(obj: TaskORM) -> Task:
    return Task(
        id=obj.id,
        project_id=obj.project_id,
        code=getattr(obj, "task_code", "") or "",
        parent_task_id=getattr(obj, "parent_task_id", None),
        wbs_code=getattr(obj, "wbs_code", "") or obj.id,
        sort_order=getattr(obj, "sort_order", 0),
        name=obj.name,
        description=obj.description,
        start_date=obj.start_date,
        end_date=obj.end_date,
        duration_days=obj.duration_days,
        status=obj.status,
        priority=obj.priority,
        percent_complete=obj.percent_complete,
        actual_start=obj.actual_start,
        actual_end=obj.actual_end,
        deadline=obj.deadline,
        is_milestone=getattr(obj, "is_milestone", False),
        version=getattr(obj, "version", 1),
    )


def assignment_to_orm(assignment: TaskAssignment) -> TaskAssignmentORM:
    return TaskAssignmentORM(
        id=assignment.id,
        task_id=assignment.task_id,
        resource_id=assignment.resource_id,
        project_resource_id=getattr(assignment, "project_resource_id", None),
        allocation_percent=assignment.allocation_percent,
        hours_logged=getattr(assignment, "hours_logged", 0.0),
        allocated_planned_hours=getattr(assignment, "allocated_planned_hours", Decimal("0")),
        version=getattr(assignment, "version", 1),
        response_status=getattr(assignment, "response_status", "pending"),
        responded_at=getattr(assignment, "responded_at", None),
    )


def assignment_from_orm(obj: TaskAssignmentORM) -> TaskAssignment:
    return TaskAssignment(
        id=obj.id,
        task_id=obj.task_id,
        resource_id=obj.resource_id,
        project_resource_id=getattr(obj, "project_resource_id", None),
        allocation_percent=obj.allocation_percent,
        hours_logged=getattr(obj, "hours_logged", 0.0),
        allocated_planned_hours=getattr(obj, "allocated_planned_hours", Decimal("0")),
        version=getattr(obj, "version", 1),
        response_status=getattr(obj, "response_status", "pending") or "pending",
        responded_at=getattr(obj, "responded_at", None),
    )


def dependency_to_orm(dependency: TaskDependency) -> TaskDependencyORM:
    return TaskDependencyORM(
        id=dependency.id,
        predecessor_task_id=dependency.predecessor_task_id,
        successor_task_id=dependency.successor_task_id,
        dependency_type=dependency.dependency_type,
        lag_days=dependency.lag_days,
        version=getattr(dependency, "version", 1),
    )


def dependency_from_orm(obj: TaskDependencyORM) -> TaskDependency:
    return TaskDependency(
        id=obj.id,
        predecessor_task_id=obj.predecessor_task_id,
        successor_task_id=obj.successor_task_id,
        dependency_type=obj.dependency_type,
        lag_days=obj.lag_days,
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "task_to_orm",
    "task_from_orm",
    "assignment_to_orm",
    "assignment_from_orm",
    "dependency_to_orm",
    "dependency_from_orm",
]
