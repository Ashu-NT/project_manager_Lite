from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.orm.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.mappers.employee import (
    employee_from_orm,
    employee_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.sites import SiteORM
from src.core.platform.employee.contracts import EmployeeRepository
from src.core.platform.employee.domain import Employee
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyEmployeeRepository(EmployeeRepository):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, employee: Employee) -> None:
        self.session.add(employee_to_orm(employee))

    def update(self, employee: Employee) -> None:
        employee.version = update_with_version_check(
            self.session,
            EmployeeORM,
            employee.id,
            getattr(employee, "version", 1),
            {
                "employee_code": employee.employee_code,
                "full_name": employee.full_name,
                "department_id": employee.department_id,
                "department": (employee.department or None),
                "site_id": employee.site_id,
                "site_name": (employee.site_name or None),
                "title": (employee.title or None),
                "employment_type": employee.employment_type,
                "email": employee.email,
                "phone": employee.phone,
                "is_active": employee.is_active,
            },
            not_found_message="Employee not found.",
            stale_message="Employee was updated by another user.",
        )

    def get(self, employee_id: str) -> Employee | None:
        obj = self.session.get(EmployeeORM, employee_id)
        return employee_from_orm(obj) if obj else None

    def get_by_code(self, employee_code: str) -> Employee | None:
        stmt = select(EmployeeORM).where(EmployeeORM.employee_code == employee_code)
        obj = self.session.execute(stmt).scalars().first()
        return employee_from_orm(obj) if obj else None

    def _organization_scope_predicate(self, organization_id: str) -> Any:
        return or_(
            SiteORM.organization_id == organization_id,
            DepartmentORM.organization_id == organization_id,
        )

    def _scoped_statement(self, organization_id: str) -> Any:
        return (
            select(EmployeeORM)
            .outerjoin(SiteORM, SiteORM.id == EmployeeORM.site_id)
            .outerjoin(DepartmentORM, DepartmentORM.id == EmployeeORM.department_id)
            .where(self._organization_scope_predicate(organization_id))
        )

    def get_for_organization(self, employee_id: str, organization_id: str) -> Employee | None:
        stmt = self._scoped_statement(organization_id).where(EmployeeORM.id == employee_id)
        obj = self.session.execute(stmt).scalars().first()
        return employee_from_orm(obj) if obj else None

    def get_by_code_for_organization(self, employee_code: str, organization_id: str) -> Employee | None:
        stmt = self._scoped_statement(organization_id).where(EmployeeORM.employee_code == employee_code)
        obj = self.session.execute(stmt).scalars().first()
        return employee_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Employee]:
        stmt = self._scoped_statement(organization_id)
        if active_only is not None:
            stmt = stmt.where(EmployeeORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(EmployeeORM.full_name.asc())).scalars().all()
        return [employee_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyEmployeeRepository",
]
