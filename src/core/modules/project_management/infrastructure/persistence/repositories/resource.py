from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.tenancy.tenant_context import TenantContext, TenantContextService
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.modules.project_management.infrastructure.persistence.mappers.resource import resource_from_orm, resource_to_orm


class SqlAlchemyResourceRepository(ResourceRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "ResourceRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
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
                "name": resource.name,
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

    def list_by_employee(self, employee_id: str) -> list[Resource]:
        stmt = self._base_stmt().where(ResourceORM.employee_id == employee_id)
        rows = self.session.execute(stmt).scalars().all()
        return [resource_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyResourceRepository"]
