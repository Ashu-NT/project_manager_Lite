from __future__ import annotations

from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM, ProjectResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.platform.infrastructure.persistence.orm.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.orm.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.sites import SiteORM
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.modules.project_management.infrastructure.persistence.mappers.resource import resource_from_orm, resource_to_orm


class SqlAlchemyResourceRepository(ResourceRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, resource: Resource) -> None:
        self.session.add(resource_to_orm(resource))

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

    def get(self, resource_id: str) -> Optional[Resource]:
        obj = self.session.get(ResourceORM, resource_id)
        return resource_from_orm(obj) if obj else None

    def list_all(self) -> List[Resource]:
        stmt = select(ResourceORM)
        rows = self.session.execute(stmt).scalars().all()
        return [resource_from_orm(row) for row in rows]

    def list_for_organization(self, organization_id: str) -> List[Resource]:
        stmt = (
            select(ResourceORM)
            .distinct()
            .outerjoin(ProjectResourceORM, ProjectResourceORM.resource_id == ResourceORM.id)
            .outerjoin(ProjectORM, ProjectORM.id == ProjectResourceORM.project_id)
            .outerjoin(EmployeeORM, EmployeeORM.id == ResourceORM.employee_id)
            .outerjoin(SiteORM, SiteORM.id == EmployeeORM.site_id)
            .outerjoin(DepartmentORM, DepartmentORM.id == EmployeeORM.department_id)
            .where(
                or_(
                    ProjectORM.organization_id == organization_id,
                    SiteORM.organization_id == organization_id,
                    DepartmentORM.organization_id == organization_id,
                )
            )
        )
        rows = self.session.execute(stmt).scalars().all()
        return [resource_from_orm(row) for row in rows]

    def list_by_employee(self, employee_id: str) -> List[Resource]:
        stmt = select(ResourceORM).where(ResourceORM.employee_id == employee_id)
        rows = self.session.execute(stmt).scalars().all()
        return [resource_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyResourceRepository"]
