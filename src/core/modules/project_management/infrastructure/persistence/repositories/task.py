from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment, TaskDependency
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskAssignmentORM, TaskDependencyORM, TaskORM
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.tenancy.tenant_context import TenantContext, TenantContextService
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.modules.project_management.infrastructure.persistence.mappers.task import (
    assignment_from_orm,
    assignment_to_orm,
    dependency_from_orm,
    dependency_to_orm,
    task_from_orm,
    task_to_orm,
)


class SqlAlchemyTaskRepository(TaskRepository):
    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "TaskRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label="access tasks"
        )

    def _project_scoped_stmt(self):
        ctx = self._context()
        return (
            select(TaskORM)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )

    def add(self, task: Task) -> None:
        self.session.add(task_to_orm(task))

    def update(self, task: Task) -> None:
        if self.get(task.id) is None:
            raise NotFoundError("Task not found.")
        task.version = update_with_version_check(
            self.session,
            TaskORM,
            task.id,
            getattr(task, "version", 1),
            {
                "project_id": task.project_id,
                "name": task.name,
                "description": task.description,
                "start_date": task.start_date,
                "end_date": task.end_date,
                "duration_days": task.duration_days,
                "status": task.status,
                "priority": task.priority,
                "percent_complete": task.percent_complete,
                "actual_start": task.actual_start,
                "actual_end": task.actual_end,
                "deadline": task.deadline,
            },
            not_found_message="Task not found.",
            stale_message="Task was updated by another user.",
        )

    def delete(self, task_id: str) -> None:
        ctx = self._context()
        in_scope = (
            select(TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                TaskORM.id == task_id,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
            .scalar_subquery()
        )
        self.session.execute(delete(TaskORM).where(TaskORM.id == in_scope))

    def get(self, task_id: str) -> Task | None:
        stmt = self._project_scoped_stmt().where(TaskORM.id == task_id)
        row = self.session.execute(stmt).scalar_one_or_none()
        return task_from_orm(row) if row else None

    def list_by_project(self, project_id: str) -> list[Task]:
        stmt = self._project_scoped_stmt().where(TaskORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [task_from_orm(row) for row in rows]


class SqlAlchemyAssignmentRepository(AssignmentRepository):
    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "AssignmentRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label="access assignments"
        )

    def _project_scoped_stmt(self):
        ctx = self._context()
        return (
            select(TaskAssignmentORM)
            .join(TaskORM, TaskAssignmentORM.task_id == TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )

    def add(self, assignment: TaskAssignment) -> None:
        self.session.add(assignment_to_orm(assignment))

    def get(self, assignment_id: str) -> TaskAssignment | None:
        stmt = self._project_scoped_stmt().where(TaskAssignmentORM.id == assignment_id)
        row = self.session.execute(stmt).scalar_one_or_none()
        return assignment_from_orm(row) if row else None

    def list_by_task(self, task_id: str) -> list[TaskAssignment]:
        stmt = self._project_scoped_stmt().where(TaskAssignmentORM.task_id == task_id)
        rows = self.session.execute(stmt).scalars().all()
        return [assignment_from_orm(row) for row in rows]

    def list_by_resource(self, resource_id: str) -> list[TaskAssignment]:
        stmt = self._project_scoped_stmt().where(TaskAssignmentORM.resource_id == resource_id)
        rows = self.session.execute(stmt).scalars().all()
        return [assignment_from_orm(row) for row in rows]

    def update(self, assignment: TaskAssignment) -> None:
        self.session.merge(assignment_to_orm(assignment))

    def delete(self, assignment_id: str) -> None:
        self.session.query(TaskAssignmentORM).filter_by(id=assignment_id).delete()

    def delete_by_task(self, task_id: str) -> None:
        self.session.query(TaskAssignmentORM).filter_by(task_id=task_id).delete()

    def list_by_assignment(self, task_id: str) -> list[TaskAssignment]:
        return self.list_by_task(task_id)

    def list_by_tasks(self, task_ids: list[str]) -> list[TaskAssignment]:
        if not task_ids:
            return []
        ctx = self._context()
        stmt = (
            select(TaskAssignmentORM)
            .join(TaskORM, TaskAssignmentORM.task_id == TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                TaskAssignmentORM.task_id.in_(task_ids),
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )
        rows = self.session.execute(stmt).scalars().all()
        return [assignment_from_orm(row) for row in rows]


class SqlAlchemyDependencyRepository(DependencyRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, dependency: TaskDependency) -> None:
        self.session.add(dependency_to_orm(dependency))

    def get(self, dependency_id: str) -> TaskDependency | None:
        obj = self.session.get(TaskDependencyORM, dependency_id)
        return dependency_from_orm(obj) if obj else None

    def update(self, dependency: TaskDependency) -> None:
        self.session.merge(dependency_to_orm(dependency))

    def list_by_project(self, project_id: str) -> list[TaskDependency]:
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

    def list_by_task(self, task_id: str) -> list[TaskDependency]:
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
