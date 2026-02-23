from __future__ import annotations

from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from core.interfaces import AssignmentRepository, DependencyRepository, TaskRepository
from core.models import Task, TaskAssignment, TaskDependency
from infra.db.mappers import (
    assignment_from_orm,
    assignment_to_orm,
    dependency_from_orm,
    dependency_to_orm,
    task_from_orm,
    task_to_orm,
)
from infra.db.models import TaskAssignmentORM, TaskDependencyORM, TaskORM


class SqlAlchemyTaskRepository(TaskRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, task: Task) -> None:
        self.session.add(task_to_orm(task))

    def update(self, task: Task) -> None:
        self.session.merge(task_to_orm(task))

    def delete(self, task_id: str) -> None:
        self.session.query(TaskORM).filter_by(id=task_id).delete()

    def get(self, task_id: str) -> Optional[Task]:
        obj = self.session.get(TaskORM, task_id)
        return task_from_orm(obj) if obj else None

    def list_by_project(self, project_id: str) -> List[Task]:
        stmt = select(TaskORM).where(TaskORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [task_from_orm(row) for row in rows]


class SqlAlchemyAssignmentRepository(AssignmentRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, assignment: TaskAssignment) -> None:
        self.session.add(assignment_to_orm(assignment))

    def get(self, assignment_id: str) -> Optional[TaskAssignment]:
        obj = self.session.get(TaskAssignmentORM, assignment_id)
        return assignment_from_orm(obj) if obj else None

    def list_by_task(self, task_id: str) -> List[TaskAssignment]:
        stmt = select(TaskAssignmentORM).where(TaskAssignmentORM.task_id == task_id)
        rows = self.session.execute(stmt).scalars().all()
        return [assignment_from_orm(row) for row in rows]

    def list_by_resource(self, resource_id: str) -> List[TaskAssignment]:
        stmt = select(TaskAssignmentORM).where(TaskAssignmentORM.resource_id == resource_id)
        rows = self.session.execute(stmt).scalars().all()
        return [assignment_from_orm(row) for row in rows]

    def update(self, assignment: TaskAssignment) -> None:
        self.session.merge(assignment_to_orm(assignment))

    def delete(self, assignment_id: str) -> None:
        self.session.query(TaskAssignmentORM).filter_by(id=assignment_id).delete()

    def delete_by_task(self, task_id: str) -> None:
        self.session.query(TaskAssignmentORM).filter_by(task_id=task_id).delete()

    def list_by_assignment(self, task_id: str) -> List[TaskAssignment]:
        stmt = select(TaskAssignmentORM).where(TaskAssignmentORM.task_id == task_id)
        rows = self.session.execute(stmt).scalars().all()
        return [assignment_from_orm(row) for row in rows]

    def list_by_tasks(self, task_ids: List[str]) -> List[TaskAssignment]:
        if not task_ids:
            return []
        stmt = select(TaskAssignmentORM).where(TaskAssignmentORM.task_id.in_(task_ids))
        rows = self.session.execute(stmt).scalars().all()
        return [assignment_from_orm(row) for row in rows]


class SqlAlchemyDependencyRepository(DependencyRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, dependency: TaskDependency) -> None:
        self.session.add(dependency_to_orm(dependency))

    def get(self, dependency_id: str) -> Optional[TaskDependency]:
        obj = self.session.get(TaskDependencyORM, dependency_id)
        return dependency_from_orm(obj) if obj else None

    def list_by_project(self, project_id: str) -> List[TaskDependency]:
        task_ids_subq = select(TaskORM.id).where(TaskORM.project_id == project_id)
        stmt = select(TaskDependencyORM).where(
            TaskDependencyORM.predecessor_task_id.in_(task_ids_subq),
            TaskDependencyORM.successor_task_id.in_(task_ids_subq),
        )
        rows = self.session.execute(stmt).scalars().all()
        return [dependency_from_orm(row) for row in rows]

    def delete(self, dependency_id: str) -> None:
        self.session.query(TaskDependencyORM).filter_by(id=dependency_id).delete()

    def delete_for_task(self, task_id: str) -> None:
        self.session.query(TaskDependencyORM).filter(
            or_(
                TaskDependencyORM.predecessor_task_id == task_id,
                TaskDependencyORM.successor_task_id == task_id,
            )
        ).delete(synchronize_session=False)

    def list_by_task(self, task_id: str) -> List[TaskDependency]:
        stmt = select(TaskDependencyORM).where(
            or_(
                TaskDependencyORM.predecessor_task_id == task_id,
                TaskDependencyORM.successor_task_id == task_id,
            )
        )
        rows = self.session.execute(stmt).scalars().all()
        return [dependency_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyTaskRepository",
    "SqlAlchemyAssignmentRepository",
    "SqlAlchemyDependencyRepository",
]
