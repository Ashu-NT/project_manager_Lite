from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.domain.projects.project import Project, ProjectResource
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM, ProjectResourceORM
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

    def list_for_organization(self, organization_id: str) -> list[Project]:
        ctx = self._context()
        if organization_id != ctx.organization_id:
            return []
        return self.list()


class SqlAlchemyProjectResourceRepository(ProjectResourceRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _scoped_project_ids(self):
        if self._tenant_context_service is None:
            return None
        ctx = self._tenant_context_service.require_organization_context(
            operation_label="access project resources"
        )
        return (
            select(ProjectORM.id).where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )

    def add(self, pr: ProjectResource) -> None:
        self.session.add(project_resource_to_orm(pr))

    def get(self, pr_id: str) -> ProjectResource | None:
        scoped_ids = self._scoped_project_ids()
        if scoped_ids is not None:
            stmt = select(ProjectResourceORM).where(
                ProjectResourceORM.id == pr_id,
                ProjectResourceORM.project_id.in_(scoped_ids),
            )
            obj = self.session.execute(stmt).scalar_one_or_none()
        else:
            obj = self.session.get(ProjectResourceORM, pr_id)
        return project_resource_from_orm(obj) if obj else None

    def list_by_project(self, project_id: str) -> list[ProjectResource]:
        stmt = select(ProjectResourceORM).where(ProjectResourceORM.project_id == project_id)
        scoped_ids = self._scoped_project_ids()
        if scoped_ids is not None:
            stmt = stmt.where(ProjectResourceORM.project_id.in_(scoped_ids))
        rows = self.session.execute(stmt).scalars().all()
        return [project_resource_from_orm(row) for row in rows]

    def get_for_project(self, project_id: str, resource_id: str) -> ProjectResource | None:
        stmt = select(ProjectResourceORM).where(
            ProjectResourceORM.project_id == project_id,
            ProjectResourceORM.resource_id == resource_id,
        )
        scoped_ids = self._scoped_project_ids()
        if scoped_ids is not None:
            stmt = stmt.where(ProjectResourceORM.project_id.in_(scoped_ids))
        obj = self.session.execute(stmt).scalars().first()
        return project_resource_from_orm(obj) if obj else None

    def delete(self, pr_id: str) -> None:
        scoped_ids = self._scoped_project_ids()
        if scoped_ids is not None:
            self.session.execute(
                delete(ProjectResourceORM).where(
                    ProjectResourceORM.id == pr_id,
                    ProjectResourceORM.project_id.in_(scoped_ids),
                )
            )
        else:
            obj = self.session.get(ProjectResourceORM, pr_id)
            if obj:
                self.session.delete(obj)

    def delete_by_resource(self, res_id: str) -> None:
        stmt = delete(ProjectResourceORM).where(ProjectResourceORM.resource_id == res_id)
        scoped_ids = self._scoped_project_ids()
        if scoped_ids is not None:
            stmt = stmt.where(ProjectResourceORM.project_id.in_(scoped_ids))
        self.session.execute(stmt)

    def update(self, pr: ProjectResource) -> None:
        self.session.merge(project_resource_to_orm(pr))


__all__ = [
    "SqlAlchemyProjectRepository",
    "SqlAlchemyProjectResourceRepository",
]
