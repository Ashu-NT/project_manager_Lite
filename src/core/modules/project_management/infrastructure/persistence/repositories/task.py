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
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
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

    def _ensure_project_in_scope(self, project_id: str) -> None:
        ctx = self._context()
        project = self.session.execute(
            select(ProjectORM.id).where(
                ProjectORM.id == project_id,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found.")

    def add(self, task: Task) -> None:
        self._ensure_project_in_scope(task.project_id)
        self.session.add(task_to_orm(task))

    def update(self, task: Task) -> None:
        if self.get(task.id) is None:
            raise NotFoundError("Task not found.")
        self._ensure_project_in_scope(task.project_id)
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
            extra_filters={"project_id": task.project_id},
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

    def _ensure_task_in_scope(self, task_id: str) -> None:
        ctx = self._context()
        task = self.session.execute(
            select(TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                TaskORM.id == task_id,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if task is None:
            raise NotFoundError("Task not found.")

    def _ensure_resource_in_scope(self, resource_id: str) -> None:
        ctx = self._context()
        resource = self.session.execute(
            select(ResourceORM.id).where(
                ResourceORM.id == resource_id,
                ResourceORM.tenant_id == ctx.tenant_id,
                ResourceORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if resource is None:
            raise NotFoundError("Resource not found.")

    def _scoped_assignment_ids(
        self,
        *,
        assignment_id: str | None = None,
        task_id: str | None = None,
    ):
        stmt = (
            select(TaskAssignmentORM.id)
            .join(TaskORM, TaskAssignmentORM.task_id == TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                ProjectORM.tenant_id == self._context().tenant_id,
                ProjectORM.organization_id == self._context().organization_id,
            )
        )
        if assignment_id is not None:
            stmt = stmt.where(TaskAssignmentORM.id == assignment_id)
        if task_id is not None:
            stmt = stmt.where(TaskAssignmentORM.task_id == task_id)
        return stmt

    def add(self, assignment: TaskAssignment) -> None:
        self._ensure_task_in_scope(assignment.task_id)
        self._ensure_resource_in_scope(assignment.resource_id)
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
        row = (
            self.session.execute(
                self._project_scoped_stmt().where(TaskAssignmentORM.id == assignment.id)
            ).scalar_one_or_none()
        )
        if row is None:
            raise NotFoundError("Assignment not found.")
        self._ensure_task_in_scope(assignment.task_id)
        self._ensure_resource_in_scope(assignment.resource_id)
        row.task_id = assignment.task_id
        row.resource_id = assignment.resource_id
        row.allocation_percent = assignment.allocation_percent
        row.hours_logged = assignment.hours_logged
        row.project_resource_id = assignment.project_resource_id

    def delete(self, assignment_id: str) -> None:
        self.session.execute(
            delete(TaskAssignmentORM).where(
                TaskAssignmentORM.id.in_(
                    self._scoped_assignment_ids(assignment_id=assignment_id)
                )
            )
        )

    def delete_by_task(self, task_id: str) -> None:
        self.session.execute(
            delete(TaskAssignmentORM).where(
                TaskAssignmentORM.id.in_(
                    self._scoped_assignment_ids(task_id=task_id)
                )
            )
        )

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
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "DependencyRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label="access dependencies"
        )

    def _scoped_task_ids(self, *, project_id: str | None = None):
        ctx = self._context()
        stmt = (
            select(TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )
        if project_id is not None:
            stmt = stmt.where(TaskORM.project_id == project_id)
        return stmt

    def _ensure_task_in_scope(self, task_id: str) -> None:
        task = self.session.execute(
            self._scoped_task_ids().where(TaskORM.id == task_id)
        ).scalar_one_or_none()
        if task is None:
            raise NotFoundError("Task not found.")

    def add(self, dependency: TaskDependency) -> None:
        self._ensure_task_in_scope(dependency.predecessor_task_id)
        self._ensure_task_in_scope(dependency.successor_task_id)
        self.session.add(dependency_to_orm(dependency))

    def get(self, dependency_id: str) -> TaskDependency | None:
        scoped_task_ids = self._scoped_task_ids()
        obj = self.session.execute(
            select(TaskDependencyORM).where(
                TaskDependencyORM.id == dependency_id,
                TaskDependencyORM.predecessor_task_id.in_(scoped_task_ids),
                TaskDependencyORM.successor_task_id.in_(scoped_task_ids),
            )
        ).scalar_one_or_none()
        return dependency_from_orm(obj) if obj else None

    def update(self, dependency: TaskDependency) -> None:
        row = self.session.execute(
            select(TaskDependencyORM).where(
                TaskDependencyORM.id == dependency.id,
                TaskDependencyORM.predecessor_task_id.in_(self._scoped_task_ids()),
                TaskDependencyORM.successor_task_id.in_(self._scoped_task_ids()),
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError("Dependency not found.")
        self._ensure_task_in_scope(dependency.predecessor_task_id)
        self._ensure_task_in_scope(dependency.successor_task_id)
        row.predecessor_task_id = dependency.predecessor_task_id
        row.successor_task_id = dependency.successor_task_id
        row.dependency_type = dependency.dependency_type
        row.lag_days = dependency.lag_days

    def list_by_project(self, project_id: str) -> list[TaskDependency]:
        task_ids_subq = self._scoped_task_ids(project_id=project_id)
        stmt = select(TaskDependencyORM).where(
            TaskDependencyORM.predecessor_task_id.in_(task_ids_subq),
            TaskDependencyORM.successor_task_id.in_(task_ids_subq),
        )
        rows = self.session.execute(stmt).scalars().all()
        return [dependency_from_orm(row) for row in rows]

    def delete(self, dependency_id: str) -> None:
        self.session.execute(
            delete(TaskDependencyORM).where(
                TaskDependencyORM.id == dependency_id,
                TaskDependencyORM.predecessor_task_id.in_(self._scoped_task_ids()),
                TaskDependencyORM.successor_task_id.in_(self._scoped_task_ids()),
            )
        )

    def delete_for_task(self, task_id: str) -> None:
        self.session.execute(
            delete(TaskDependencyORM).where(
                or_(
                    TaskDependencyORM.predecessor_task_id == task_id,
                    TaskDependencyORM.successor_task_id == task_id,
                ),
                TaskDependencyORM.predecessor_task_id.in_(self._scoped_task_ids()),
                TaskDependencyORM.successor_task_id.in_(self._scoped_task_ids()),
            )
        )

    def list_by_task(self, task_id: str) -> list[TaskDependency]:
        stmt = select(TaskDependencyORM).where(
            or_(
                TaskDependencyORM.predecessor_task_id == task_id,
                TaskDependencyORM.successor_task_id == task_id,
            ),
            TaskDependencyORM.predecessor_task_id.in_(self._scoped_task_ids()),
            TaskDependencyORM.successor_task_id.in_(self._scoped_task_ids()),
        )
        rows = self.session.execute(stmt).scalars().all()
        return [dependency_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyTaskRepository",
    "SqlAlchemyAssignmentRepository",
    "SqlAlchemyDependencyRepository",
]
