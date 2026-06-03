from __future__ import annotations

from typing import List, Optional

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
    def __init__(self, session: Session):
        self.session = session

    def add(self, department: Department) -> None:
        self.session.add(department_to_orm(department))

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

    def get(self, department_id: str) -> Optional[Department]:
        obj = self.session.get(DepartmentORM, department_id)
        return department_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, department_code: str) -> Optional[Department]:
        stmt = select(DepartmentORM).where(
            DepartmentORM.organization_id == organization_id,
            DepartmentORM.department_code == department_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return department_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> List[Department]:
        stmt = select(DepartmentORM).where(DepartmentORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(DepartmentORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(DepartmentORM.name.asc())).scalars().all()
        return [department_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyDepartmentRepository",
]
