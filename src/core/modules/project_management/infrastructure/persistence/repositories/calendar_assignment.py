"""SQLAlchemy repositories for PM calendar assignment domain."""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.domain.calendar.assignment import (
    ProjectCalendarAssignment,
    ResourceCalendarAssignment,
)
from src.core.modules.project_management.infrastructure.persistence.orm.calendar_assignment import (
    ProjectCalendarAssignmentORM,
    ResourceCalendarAssignmentORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.repositories._tenant_scope import (
    ProjectManagementParentScopedRepositorySupport,
)
from src.core.platform.tenancy.tenant_context import TenantContextService


def _project_from_orm(obj: ProjectCalendarAssignmentORM) -> ProjectCalendarAssignment:
    return ProjectCalendarAssignment(
        id=obj.id,
        project_id=obj.project_id,
        calendar_id=obj.calendar_id,
        effective_from=obj.effective_from,
        effective_to=obj.effective_to,
        is_default=obj.is_default,
        priority=obj.priority,
    )


def _resource_from_orm(obj: ResourceCalendarAssignmentORM) -> ResourceCalendarAssignment:
    return ResourceCalendarAssignment(
        id=obj.id,
        resource_id=obj.resource_id,
        calendar_id=obj.calendar_id,
        effective_from=obj.effective_from,
        effective_to=obj.effective_to,
        is_default=obj.is_default,
        priority=obj.priority,
    )


def _is_effective(effective_from, effective_to, at_date: date | None) -> bool:
    if at_date is None:
        return True
    if effective_from is not None and at_date < effective_from:
        return False
    if effective_to is not None and at_date > effective_to:
        return False
    return True


class SqlAlchemyProjectCalendarAssignmentRepository(
    ProjectManagementParentScopedRepositorySupport
):
    _repository_label = "Project calendar assignment repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._session = session
        self._tenant_context_service: TenantContextService | None = None

    def _project_assignment_scoped_stmt(self, *, operation_label: str):
        return self._scoped_stmt_for_anchor(
            ProjectCalendarAssignmentORM,
            ProjectORM,
            joins=((ProjectORM, ProjectCalendarAssignmentORM.project_id == ProjectORM.id),),
            operation_label=operation_label,
        )

    def _ensure_project_in_scope(self, project_id: str) -> None:
        self._require_anchor_in_scope(
            ProjectORM,
            project_id,
            operation_label="manage project calendar assignments",
            not_found_message="Project not found.",
        )

    def get(
        self, project_id: str, *, at_date: date | None = None
    ) -> ProjectCalendarAssignment | None:
        stmt = self._project_assignment_scoped_stmt(
            operation_label="access project calendar assignments"
        ).where(
            ProjectCalendarAssignmentORM.project_id == project_id
        ).order_by(
            ProjectCalendarAssignmentORM.priority.desc(),
            ProjectCalendarAssignmentORM.is_default.desc(),
        )
        rows = self.session.execute(stmt).scalars().all()
        for row in rows:
            if _is_effective(row.effective_from, row.effective_to, at_date):
                return _project_from_orm(row)
        return None

    def list_for_project(self, project_id: str) -> list[ProjectCalendarAssignment]:
        stmt = self._project_assignment_scoped_stmt(
            operation_label="access project calendar assignments"
        ).where(
            ProjectCalendarAssignmentORM.project_id == project_id
        ).order_by(ProjectCalendarAssignmentORM.priority.desc())
        rows = self.session.execute(stmt).scalars().all()
        return [_project_from_orm(r) for r in rows]

    def list_for_calendar(self, calendar_id: str) -> list[ProjectCalendarAssignment]:
        stmt = self._project_assignment_scoped_stmt(
            operation_label="access project calendar assignments"
        ).where(
            ProjectCalendarAssignmentORM.calendar_id == calendar_id
        )
        rows = self.session.execute(stmt).scalars().all()
        return [_project_from_orm(r) for r in rows]

    def save(self, assignment: ProjectCalendarAssignment) -> None:
        self._ensure_project_in_scope(assignment.project_id)
        existing = self._get_via_anchor_in_scope(
            ProjectCalendarAssignmentORM,
            ProjectORM,
            joins=((ProjectORM, ProjectCalendarAssignmentORM.project_id == ProjectORM.id),),
            record_id=assignment.id,
            operation_label="manage project calendar assignments",
        )
        if existing:
            existing.project_id = assignment.project_id
            existing.calendar_id = assignment.calendar_id
            existing.effective_from = assignment.effective_from
            existing.effective_to = assignment.effective_to
            existing.is_default = assignment.is_default
            existing.priority = assignment.priority
        else:
            self.session.add(
                ProjectCalendarAssignmentORM(
                    id=assignment.id,
                    project_id=assignment.project_id,
                    calendar_id=assignment.calendar_id,
                    effective_from=assignment.effective_from,
                    effective_to=assignment.effective_to,
                    is_default=assignment.is_default,
                    priority=assignment.priority,
                )
            )

    def delete(self, assignment_id: str) -> None:
        scoped_ids = (
            self._project_assignment_scoped_stmt(
                operation_label="manage project calendar assignments"
            )
            .where(ProjectCalendarAssignmentORM.id == assignment_id)
            .with_only_columns(ProjectCalendarAssignmentORM.id)
            .scalar_subquery()
        )
        self.session.execute(
            delete(ProjectCalendarAssignmentORM).where(
                ProjectCalendarAssignmentORM.id == scoped_ids
            )
        )


class SqlAlchemyResourceCalendarAssignmentRepository(
    ProjectManagementParentScopedRepositorySupport
):
    _repository_label = "Resource calendar assignment repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._session = session
        self._tenant_context_service: TenantContextService | None = None

    def _resource_assignment_scoped_stmt(self, *, operation_label: str):
        return self._scoped_stmt_for_anchor(
            ResourceCalendarAssignmentORM,
            ResourceORM,
            joins=((ResourceORM, ResourceCalendarAssignmentORM.resource_id == ResourceORM.id),),
            operation_label=operation_label,
        )

    def _ensure_resource_in_scope(self, resource_id: str) -> None:
        self._require_anchor_in_scope(
            ResourceORM,
            resource_id,
            operation_label="manage resource calendar assignments",
            not_found_message="Resource not found.",
        )

    def get(
        self, resource_id: str, *, at_date: date | None = None
    ) -> ResourceCalendarAssignment | None:
        stmt = self._resource_assignment_scoped_stmt(
            operation_label="access resource calendar assignments"
        ).where(
            ResourceCalendarAssignmentORM.resource_id == resource_id
        ).order_by(
            ResourceCalendarAssignmentORM.priority.desc(),
            ResourceCalendarAssignmentORM.is_default.desc(),
        )
        rows = self.session.execute(stmt).scalars().all()
        for row in rows:
            if _is_effective(row.effective_from, row.effective_to, at_date):
                return _resource_from_orm(row)
        return None

    def list_for_resource(self, resource_id: str) -> list[ResourceCalendarAssignment]:
        stmt = self._resource_assignment_scoped_stmt(
            operation_label="access resource calendar assignments"
        ).where(
            ResourceCalendarAssignmentORM.resource_id == resource_id
        ).order_by(ResourceCalendarAssignmentORM.priority.desc())
        rows = self.session.execute(stmt).scalars().all()
        return [_resource_from_orm(r) for r in rows]

    def list_for_calendar(self, calendar_id: str) -> list[ResourceCalendarAssignment]:
        stmt = self._resource_assignment_scoped_stmt(
            operation_label="access resource calendar assignments"
        ).where(
            ResourceCalendarAssignmentORM.calendar_id == calendar_id
        )
        rows = self.session.execute(stmt).scalars().all()
        return [_resource_from_orm(r) for r in rows]

    def save(self, assignment: ResourceCalendarAssignment) -> None:
        self._ensure_resource_in_scope(assignment.resource_id)
        existing = self._get_via_anchor_in_scope(
            ResourceCalendarAssignmentORM,
            ResourceORM,
            joins=((ResourceORM, ResourceCalendarAssignmentORM.resource_id == ResourceORM.id),),
            record_id=assignment.id,
            operation_label="manage resource calendar assignments",
        )
        if existing:
            existing.resource_id = assignment.resource_id
            existing.calendar_id = assignment.calendar_id
            existing.effective_from = assignment.effective_from
            existing.effective_to = assignment.effective_to
            existing.is_default = assignment.is_default
            existing.priority = assignment.priority
        else:
            self.session.add(
                ResourceCalendarAssignmentORM(
                    id=assignment.id,
                    resource_id=assignment.resource_id,
                    calendar_id=assignment.calendar_id,
                    effective_from=assignment.effective_from,
                    effective_to=assignment.effective_to,
                    is_default=assignment.is_default,
                    priority=assignment.priority,
                )
            )

    def delete(self, assignment_id: str) -> None:
        scoped_ids = (
            self._resource_assignment_scoped_stmt(
                operation_label="manage resource calendar assignments"
            )
            .where(ResourceCalendarAssignmentORM.id == assignment_id)
            .with_only_columns(ResourceCalendarAssignmentORM.id)
            .scalar_subquery()
        )
        self.session.execute(
            delete(ResourceCalendarAssignmentORM).where(
                ResourceCalendarAssignmentORM.id == scoped_ids
            )
        )


__all__ = [
    "SqlAlchemyProjectCalendarAssignmentRepository",
    "SqlAlchemyResourceCalendarAssignmentRepository",
]
