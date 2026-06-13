from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.domain.projects.project import Project, ProjectResource
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM, ProjectResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.repositories._tenant_scope import (
    ProjectManagementParentScopedRepositorySupport,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.tenancy.tenant_context import TenantContext, TenantContextService
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.modules.project_management.infrastructure.persistence.mappers.project import (
    project_from_orm,
    project_resource_from_orm,
    project_resource_to_orm,
    project_to_orm,
)


class SqlAlchemyProjectRepository(ProjectRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "ProjectRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label="access projects"
        )

    def _base_stmt(self):
        ctx = self._context()
        return select(ProjectORM).where(
            ProjectORM.tenant_id == ctx.tenant_id,
            ProjectORM.organization_id == ctx.organization_id,
        )

    def add(self, project: Project) -> None:
        ctx = self._context()
        orm = project_to_orm(project)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self.session.add(orm)

    def update(self, project: Project) -> None:
        ctx = self._context()
        project.version = update_with_version_check(
            self.session,
            ProjectORM,
            project.id,
            getattr(project, "version", 1),
            {
                "name": project.name,
                "description": project.description,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "status": project.status,
                "client_name": project.client_name,
                "client_contact": project.client_contact,
                "planned_budget": project.planned_budget,
                "currency": project.currency,
            },
            extra_filters={
                "tenant_id": ctx.tenant_id,
                "organization_id": ctx.organization_id,
            },
            not_found_message="Project not found.",
            stale_message="Project was updated by another user.",
        )

    def delete(self, project_id: str) -> None:
        ctx = self._context()
        self.session.execute(
            delete(ProjectORM).where(
                ProjectORM.id == project_id,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )

    def get(self, project_id: str) -> Project | None:
        stmt = self._base_stmt().where(ProjectORM.id == project_id)
        row = self.session.execute(stmt).scalar_one_or_none()
        return project_from_orm(row) if row else None

    def list(self) -> list[Project]:
        rows = self.session.execute(self._base_stmt()).scalars().all()
        return [project_from_orm(row) for row in rows]


class SqlAlchemyProjectResourceRepository(
    ProjectManagementParentScopedRepositorySupport,
    ProjectResourceRepository,
):
    _repository_label = "Project resource repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _project_resource_scoped_stmt(self, *, operation_label: str):
        return self._scoped_stmt_for_anchor(
            ProjectResourceORM,
            ProjectORM,
            joins=((ProjectORM, ProjectResourceORM.project_id == ProjectORM.id),),
            operation_label=operation_label,
        )

    def _ensure_project_in_scope(self, project_id: str) -> None:
        self._require_anchor_in_scope(
            ProjectORM,
            project_id,
            operation_label="manage project resources",
            not_found_message="Project not found.",
        )

    def _ensure_resource_in_scope(self, resource_id: str) -> None:
        self._require_anchor_in_scope(
            ResourceORM,
            resource_id,
            operation_label="manage project resources",
            not_found_message="Resource not found.",
        )

    def add(self, pr: ProjectResource) -> None:
        self._ensure_project_in_scope(pr.project_id)
        self._ensure_resource_in_scope(pr.resource_id)
        self.session.add(project_resource_to_orm(pr))

    def get(self, pr_id: str) -> ProjectResource | None:
        stmt = self._project_resource_scoped_stmt(
            operation_label="access project resources"
        ).where(ProjectResourceORM.id == pr_id)
        obj = self.session.execute(stmt).scalar_one_or_none()
        return project_resource_from_orm(obj) if obj else None

    def list_by_project(self, project_id: str) -> list[ProjectResource]:
        stmt = self._project_resource_scoped_stmt(
            operation_label="access project resources"
        ).where(ProjectResourceORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [project_resource_from_orm(row) for row in rows]

    def get_for_project(self, project_id: str, resource_id: str) -> ProjectResource | None:
        stmt = self._project_resource_scoped_stmt(
            operation_label="access project resources"
        ).where(
            ProjectResourceORM.project_id == project_id,
            ProjectResourceORM.resource_id == resource_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return project_resource_from_orm(obj) if obj else None

    def delete(self, pr_id: str) -> None:
        scoped_ids = (
            self._project_resource_scoped_stmt(operation_label="manage project resources")
            .where(ProjectResourceORM.id == pr_id)
            .with_only_columns(ProjectResourceORM.id)
            .scalar_subquery()
        )
        self.session.execute(delete(ProjectResourceORM).where(ProjectResourceORM.id == scoped_ids))

    def delete_by_resource(self, res_id: str) -> None:
        scoped_ids = (
            self._project_resource_scoped_stmt(operation_label="manage project resources")
            .where(ProjectResourceORM.resource_id == res_id)
            .with_only_columns(ProjectResourceORM.id)
        )
        self.session.execute(
            delete(ProjectResourceORM).where(ProjectResourceORM.id.in_(scoped_ids))
        )

    def update(self, pr: ProjectResource) -> None:
        row = self._require_via_anchor_in_scope(
            ProjectResourceORM,
            ProjectORM,
            joins=((ProjectORM, ProjectResourceORM.project_id == ProjectORM.id),),
            record_id=pr.id,
            operation_label="manage project resources",
            not_found_message="Project resource not found.",
        )
        self._ensure_project_in_scope(pr.project_id)
        self._ensure_resource_in_scope(pr.resource_id)
        row.project_id = pr.project_id
        row.resource_id = pr.resource_id
        row.hourly_rate = pr.hourly_rate
        row.currency_code = pr.currency_code
        row.planned_hours = pr.planned_hours
        row.is_active = pr.is_active


__all__ = [
    "SqlAlchemyProjectRepository",
    "SqlAlchemyProjectResourceRepository",
]
