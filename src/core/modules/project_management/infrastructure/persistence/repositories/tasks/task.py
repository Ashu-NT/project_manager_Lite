from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
    TimesheetAssignmentContext,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment, TaskDependency
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskAssignmentORM, TaskDependencyORM, TaskORM
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds, TenantContextService
from src.infra.persistence.db.optimistic import delete_with_version_check, update_with_version_check
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

    def _context(self) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "TaskRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
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
                "task_code": getattr(task, "code", "") or None,
                "parent_task_id": task.parent_task_id,
                "wbs_code": task.wbs_code,
                "sort_order": task.sort_order,
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
                "constraint_type": (
                    task.constraint_type.value if task.constraint_type is not None else None
                ),
                "constraint_date": task.constraint_date,
                "is_milestone": task.is_milestone,
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
        stmt = (
            self._project_scoped_stmt()
            .where(TaskORM.project_id == project_id)
            .order_by(TaskORM.sort_order, TaskORM.wbs_code, TaskORM.id)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [task_from_orm(row) for row in rows]

    def list_by_ids(self, task_ids: list[str]) -> list[Task]:
        if not task_ids:
            return []
        stmt = self._project_scoped_stmt().where(TaskORM.id.in_(set(task_ids)))
        rows = self.session.execute(stmt).scalars().all()
        return [task_from_orm(row) for row in rows]

    def list_children(self, project_id: str, parent_task_id: str | None) -> list[Task]:
        stmt = (
            self._project_scoped_stmt()
            .where(
                TaskORM.project_id == project_id,
                TaskORM.parent_task_id == parent_task_id,
            )
            .order_by(TaskORM.sort_order, TaskORM.wbs_code, TaskORM.id)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [task_from_orm(row) for row in rows]


class SqlAlchemyAssignmentRepository(AssignmentRepository):
    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "AssignmentRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
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
        ctx = self._context()
        stmt = (
            select(TaskAssignmentORM.id)
            .join(TaskORM, TaskAssignmentORM.task_id == TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
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

    def list_by_ids(self, assignment_ids: list[str]) -> list[TaskAssignment]:
        if not assignment_ids:
            return []
        stmt = self._project_scoped_stmt().where(TaskAssignmentORM.id.in_(set(assignment_ids)))
        rows = self.session.execute(stmt).scalars().all()
        return [assignment_from_orm(row) for row in rows]

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
        row.allocated_planned_hours = assignment.allocated_planned_hours
        row.project_resource_id = assignment.project_resource_id
        row.response_status = assignment.response_status
        row.responded_at = assignment.responded_at

    def update_planned_hours_with_version_check(
        self, assignment: TaskAssignment, *, expected_version: int
    ) -> TaskAssignment:
        self._ensure_task_in_scope(assignment.task_id)
        assignment.version = update_with_version_check(
            self.session,
            TaskAssignmentORM,
            assignment.id,
            expected_version,
            {"allocated_planned_hours": assignment.allocated_planned_hours},
            not_found_message="Assignment not found.",
            stale_message="Assignment was updated by another user.",
        )
        return assignment

    def update_allocation_with_version_check(
        self, assignment: TaskAssignment, *, expected_version: int
    ) -> TaskAssignment:
        self._ensure_task_in_scope(assignment.task_id)
        assignment.version = update_with_version_check(
            self.session,
            TaskAssignmentORM,
            assignment.id,
            expected_version,
            {"allocation_percent": assignment.allocation_percent},
            not_found_message="Assignment not found.",
            stale_message="Assignment was updated by another user.",
        )
        return assignment

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

    def list_timesheet_contexts(
        self,
        *,
        project_id: str | None = None,
        assignment_id: str | None = None,
    ) -> list[TimesheetAssignmentContext]:
        ctx = self._context()
        stmt = (
            select(
                TaskAssignmentORM.id,
                ProjectORM.id,
                ProjectORM.name,
                TaskORM.id,
                TaskORM.name,
                ResourceORM.id,
                ResourceORM.name,
            )
            .join(TaskORM, TaskAssignmentORM.task_id == TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .join(ResourceORM, TaskAssignmentORM.resource_id == ResourceORM.id)
            .where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
                ResourceORM.tenant_id == ctx.tenant_id,
                ResourceORM.organization_id == ctx.organization_id,
            )
        )
        if project_id is not None:
            stmt = stmt.where(ProjectORM.id == project_id)
        if assignment_id is not None:
            stmt = stmt.where(TaskAssignmentORM.id == assignment_id)
        rows = self.session.execute(
            stmt.order_by(ProjectORM.name, TaskORM.name, ResourceORM.name)
        ).all()
        return [
            TimesheetAssignmentContext(
                assignment_id=row[0],
                project_id=row[1],
                project_name=row[2],
                task_id=row[3],
                task_name=row[4],
                resource_id=row[5],
                resource_name=row[6],
            )
            for row in rows
        ]


class SqlAlchemyDependencyRepository(DependencyRepository):
    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "DependencyRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
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

    def _ensure_same_project(self, predecessor_task_id: str, successor_task_id: str) -> None:
        """Defense-in-depth (§9/§G5 of the R4.4 dependency audit): the
        schema cannot express "both endpoints in the same project" --
        task_dependencies has no project_id column and its FKs target
        tasks.id alone, not the (project_id, id) composite tasks carries
        for its own self-referential FK. A caller that reaches this
        repository directly (bypassing TaskDependencyMixin's
        DEPENDENCY_CROSS_PROJECT diagnostics check) would otherwise be able
        to persist a cross-project edge as long as both tasks share a
        tenant/org."""
        ctx = self._context()
        rows = self.session.execute(
            select(TaskORM.id, TaskORM.project_id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                TaskORM.id.in_((predecessor_task_id, successor_task_id)),
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        ).all()
        project_ids = {row[1] for row in rows}
        if len(project_ids) > 1:
            raise BusinessRuleError(
                "Dependencies are allowed only between tasks in the same project.",
                code="DEPENDENCY_CROSS_PROJECT",
            )

    def add(self, dependency: TaskDependency) -> None:
        self._ensure_task_in_scope(dependency.predecessor_task_id)
        self._ensure_task_in_scope(dependency.successor_task_id)
        self._ensure_same_project(dependency.predecessor_task_id, dependency.successor_task_id)
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
        # Defense-in-depth (§G5): both endpoints must belong to the same
        # project. The DB schema cannot express this (task_dependencies has
        # no project_id column, and the FKs target tasks.id alone), so it
        # is enforced here and in the application-layer diagnostics check.
        self._ensure_same_project(dependency.predecessor_task_id, dependency.successor_task_id)
        dependency.version = update_with_version_check(
            self.session,
            TaskDependencyORM,
            dependency.id,
            getattr(dependency, "version", 1),
            {
                "predecessor_task_id": dependency.predecessor_task_id,
                "successor_task_id": dependency.successor_task_id,
                "dependency_type": dependency.dependency_type,
                "lag_days": dependency.lag_days,
            },
            not_found_message="Dependency not found.",
            stale_message="Dependency was updated by another user.",
        )

    def list_by_project(self, project_id: str) -> list[TaskDependency]:
        task_ids_subq = self._scoped_task_ids(project_id=project_id)
        stmt = select(TaskDependencyORM).where(
            TaskDependencyORM.predecessor_task_id.in_(task_ids_subq),
            TaskDependencyORM.successor_task_id.in_(task_ids_subq),
        )
        rows = self.session.execute(stmt).scalars().all()
        return [dependency_from_orm(row) for row in rows]

    def delete(self, dependency_id: str, *, expected_version: int) -> None:
        # Scope-check first (tenant/org), same as every other method here,
        # so an out-of-scope id reports NotFoundError rather than leaking
        # through as a stale-version conflict.
        in_scope = self.session.execute(
            select(TaskDependencyORM.id).where(
                TaskDependencyORM.id == dependency_id,
                TaskDependencyORM.predecessor_task_id.in_(self._scoped_task_ids()),
                TaskDependencyORM.successor_task_id.in_(self._scoped_task_ids()),
            )
        ).scalar_one_or_none()
        if in_scope is None:
            raise NotFoundError("Dependency not found.")
        delete_with_version_check(
            self.session,
            TaskDependencyORM,
            dependency_id,
            expected_version,
            not_found_message="Dependency not found.",
            stale_message="Dependency was updated by another user.",
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
