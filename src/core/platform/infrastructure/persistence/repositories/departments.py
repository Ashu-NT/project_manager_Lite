from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.mappers.departments import (
    department_from_orm,
    department_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.departments import DepartmentORM
from src.core.platform.department.contracts import DepartmentRepository
from src.core.platform.department.domain import Department
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyDepartmentRepository(DepartmentRepository):
    session: Session

    def __init__(self, session: Session, *, tenant_id_provider=None) -> None:
        self.session = session
        self._tenant_id_provider = tenant_id_provider or (lambda: None)

    def add(self, department: Department) -> None:
        orm = department_to_orm(department)
        if orm.tenant_id is None:
            orm.tenant_id = self._tenant_id_provider()
        self.session.add(orm)

    def update(self, department: Department) -> None:
        department.version = update_with_version_check(
            self.session,
            DepartmentORM,
            department.id,
            getattr(department, "version", 1),
            {
                "department_code": department.department_code,
                "name": department.name,
                "description": department.description or None,
                "site_id": department.site_id,
                "default_location_id": department.default_location_id,
                "parent_department_id": department.parent_department_id,
                "department_type": department.department_type or None,
                "cost_center_code": department.cost_center_code or None,
                "manager_employee_id": department.manager_employee_id,
                "is_active": department.is_active,
                "created_at": department.created_at,
                "updated_at": department.updated_at,
                "notes": department.notes or None,
            },
            not_found_message="Department not found.",
            stale_message="Department was updated by another user.",
        )

    def get(self, department_id: str) -> Department | None:
        obj = self.session.get(DepartmentORM, department_id)
        if obj is None:
            return None
        _tid = self._tenant_id_provider()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return department_from_orm(obj)

    def get_by_code(self, organization_id: str, department_code: str) -> Department | None:
        _tid = self._tenant_id_provider()
        stmt = select(DepartmentORM).where(
            DepartmentORM.organization_id == organization_id,
            DepartmentORM.department_code == department_code,
        )
        if _tid is not None:
            stmt = stmt.where(DepartmentORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalars().first()
        return department_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Department]:
        _tid = self._tenant_id_provider()
        stmt = select(DepartmentORM).where(DepartmentORM.organization_id == organization_id)
        if _tid is not None:
            stmt = stmt.where(DepartmentORM.tenant_id == _tid)
        if active_only is not None:
            stmt = stmt.where(DepartmentORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(DepartmentORM.name.asc())).scalars().all()
        return [department_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyDepartmentRepository",
]
