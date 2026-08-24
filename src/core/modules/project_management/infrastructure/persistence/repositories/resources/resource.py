from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceReferenceSummary,
    ResourceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
    ProjectResourceORM,
)
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.skills import (
    ResourceCertificationORM,
    ResourceSkillORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)
from src.core.platform.infrastructure.persistence.orm.time_management.time.time import TimeEntryORM
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds, TenantContextService
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.modules.project_management.infrastructure.persistence.mappers.resource import resource_from_orm, resource_to_orm


class SqlAlchemyResourceRepository(ResourceRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "ResourceRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label="access resources"
        )

    def _base_stmt(self):
        ctx = self._context()
        return select(ResourceORM).where(
            ResourceORM.tenant_id == ctx.tenant_id,
            ResourceORM.organization_id == ctx.organization_id,
        )

    def add(self, resource: Resource) -> None:
        ctx = self._context()
        orm = resource_to_orm(resource)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self.session.add(orm)

    def update(self, resource: Resource) -> None:
        ctx = self._context()
        resource.version = update_with_version_check(
            self.session,
            ResourceORM,
            resource.id,
            getattr(resource, "version", 1),
            {
                "resource_code": getattr(resource, "code", "") or None,
                "name": resource.name,
                "kind": resource.kind,
                "role": resource.role,
                "hourly_rate": resource.hourly_rate,
                "is_active": resource.is_active,
                "capacity_percent": float(getattr(resource, "capacity_percent", 100.0) or 100.0),
                "address": (getattr(resource, "address", "") or None),
                "contact": (getattr(resource, "contact", "") or None),
                "cost_type": resource.cost_type,
                "currency_code": resource.currency_code,
                "worker_type": getattr(resource, "worker_type", None),
                "employee_id": getattr(resource, "employee_id", None),
                "department_id": getattr(resource, "department_id", None),
                "site_id": getattr(resource, "site_id", None),
            },
            extra_filters={
                "tenant_id": ctx.tenant_id,
                "organization_id": ctx.organization_id,
            },
            not_found_message="Resource not found.",
            stale_message="Resource was updated by another user.",
        )

    def delete(self, resource_id: str) -> None:
        ctx = self._context()
        self.session.execute(
            delete(ResourceORM).where(
                ResourceORM.id == resource_id,
                ResourceORM.tenant_id == ctx.tenant_id,
                ResourceORM.organization_id == ctx.organization_id,
            )
        )

    def get(self, resource_id: str) -> Resource | None:
        stmt = self._base_stmt().where(ResourceORM.id == resource_id)
        row = self.session.execute(stmt).scalar_one_or_none()
        return resource_from_orm(row) if row else None

    def list(self) -> list[Resource]:
        rows = self.session.execute(self._base_stmt()).scalars().all()
        return [resource_from_orm(row) for row in rows]

    def list_by_ids(self, resource_ids: list[str]) -> list[Resource]:
        if not resource_ids:
            return []
        stmt = self._base_stmt().where(ResourceORM.id.in_(set(resource_ids)))
        rows = self.session.execute(stmt).scalars().all()
        return [resource_from_orm(row) for row in rows]

    def list_by_employee(self, employee_id: str) -> list[Resource]:
        stmt = self._base_stmt().where(ResourceORM.employee_id == employee_id)
        rows = self.session.execute(stmt).scalars().all()
        return [resource_from_orm(row) for row in rows]

    def code_exists(self, code: str, *, exclude_id: str | None = None) -> bool:
        normalized = str(code or "").strip().upper()
        if not normalized:
            return False
        stmt = self._base_stmt().where(func.upper(ResourceORM.resource_code) == normalized)
        if exclude_id:
            stmt = stmt.where(ResourceORM.id != exclude_id)
        return self.session.execute(stmt.limit(1)).scalar_one_or_none() is not None

    def employee_link_exists(
        self,
        employee_id: str,
        *,
        exclude_id: str | None = None,
    ) -> bool:
        stmt = self._base_stmt().where(ResourceORM.employee_id == employee_id)
        if exclude_id:
            stmt = stmt.where(ResourceORM.id != exclude_id)
        return self.session.execute(stmt.limit(1)).scalar_one_or_none() is not None

    def reference_summary(self, resource_id: str) -> ResourceReferenceSummary:
        ctx = self._context()
        project_resources = (
            select(func.count(ProjectResourceORM.id))
            .join(ProjectORM, ProjectORM.id == ProjectResourceORM.project_id)
            .where(
                ProjectResourceORM.resource_id == resource_id,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
            .scalar_subquery()
        )
        assignments = (
            select(func.count(TaskAssignmentORM.id))
            .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(
                TaskAssignmentORM.resource_id == resource_id,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
            .scalar_subquery()
        )
        time_entries = (
            select(func.count(TimeEntryORM.id))
            .join(TaskAssignmentORM, TaskAssignmentORM.id == TimeEntryORM.assignment_id)
            .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(
                TaskAssignmentORM.resource_id == resource_id,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
            .scalar_subquery()
        )
        skills = select(func.count(ResourceSkillORM.id)).where(
            ResourceSkillORM.resource_id == resource_id
        ).scalar_subquery()
        certifications = select(func.count(ResourceCertificationORM.id)).where(
            ResourceCertificationORM.resource_id == resource_id
        ).scalar_subquery()
        row = self.session.execute(
            select(project_resources, assignments, time_entries, skills, certifications)
        ).one()
        return ResourceReferenceSummary(
            project_resources=int(row[0] or 0),
            task_assignments=int(row[1] or 0),
            time_entries=int(row[2] or 0),
            skills=int(row[3] or 0),
            certifications=int(row[4] or 0),
        )


__all__ = ["SqlAlchemyResourceRepository"]
