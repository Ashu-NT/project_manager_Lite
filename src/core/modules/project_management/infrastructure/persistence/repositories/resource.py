from __future__ import annotations


from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.modules.project_management.infrastructure.persistence.mappers.resource import resource_from_orm, resource_to_orm


class SqlAlchemyResourceRepository(ResourceRepository):
    def __init__(self, session: Session, *, tenant_id_provider=None):
        self.session = session
        self._tenant_id_provider = tenant_id_provider or (lambda: None)

    def add(self, resource: Resource) -> None:
        orm = resource_to_orm(resource)
        if orm.tenant_id is None:
            orm.tenant_id = self._tenant_id_provider()
        self.session.add(orm)

    def update(self, resource: Resource) -> None:
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
            not_found_message="Resource not found.",
            stale_message="Resource was updated by another user.",
        )

    def delete(self, resource_id: str) -> None:
        self.session.query(ResourceORM).filter_by(id=resource_id).delete()

    def get(self, resource_id: str) -> Resource | None:
        obj = self.session.get(ResourceORM, resource_id)
        return resource_from_orm(obj) if obj else None

    def get_for_organization(self, resource_id: str, organization_id: str) -> Resource | None:
        stmt = (
            select(ResourceORM)
            .where(ResourceORM.id == resource_id)
            .where(ResourceORM.organization_id == organization_id)
        )
        obj = self.session.execute(stmt).scalars().first()
        return resource_from_orm(obj) if obj else None

    def list_for_organization(self, organization_id: str) -> list[Resource]:
        stmt = select(ResourceORM).where(ResourceORM.organization_id == organization_id)
        rows = self.session.execute(stmt).scalars().all()
        return [resource_from_orm(row) for row in rows]

    def list_by_employee(self, employee_id: str) -> list[Resource]:
        stmt = select(ResourceORM).where(ResourceORM.employee_id == employee_id)
        rows = self.session.execute(stmt).scalars().all()
        return [resource_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyResourceRepository"]
