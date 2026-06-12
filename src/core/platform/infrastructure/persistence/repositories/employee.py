from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.mappers.employee import (
    employee_from_orm,
    employee_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.employee import EmployeeORM
from src.core.platform.employee.contracts import EmployeeRepository
from src.core.platform.employee.domain import Employee
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyEmployeeRepository(EmployeeRepository):
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def _get_active_tid(self) -> str | None:
        return self._tenant_context_service.get_active_tenant_id() if self._tenant_context_service else None

    def add(self, employee: Employee) -> None:
        orm = employee_to_orm(employee)
        if orm.tenant_id is None:
            orm.tenant_id = self._get_active_tid()
        self.session.add(orm)

    def update(self, employee: Employee) -> None:
        employee.version = update_with_version_check(
            self.session,
            EmployeeORM,
            employee.id,
            getattr(employee, "version", 1),
            {
                "organization_id": employee.organization_id,
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
        _tid = self._get_active_tid()
        stmt = select(EmployeeORM).where(EmployeeORM.id == employee_id)
        if _tid is not None:
            stmt = stmt.where(EmployeeORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalar_one_or_none()
        return employee_from_orm(obj) if obj else None

    def get_by_code(self, employee_code: str) -> Employee | None:
        _tid = self._get_active_tid()
        stmt = select(EmployeeORM).where(EmployeeORM.employee_code == employee_code)
        if _tid is not None:
            stmt = stmt.where(EmployeeORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalars().first()
        return employee_from_orm(obj) if obj else None

    def get_for_organization(self, employee_id: str, organization_id: str) -> Employee | None:
        _tid = self._get_active_tid()
        stmt = select(EmployeeORM).where(
            EmployeeORM.id == employee_id,
            EmployeeORM.organization_id == organization_id,
        )
        if _tid is not None:
            stmt = stmt.where(EmployeeORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalars().first()
        return employee_from_orm(obj) if obj else None

    def get_by_code_for_organization(self, employee_code: str, organization_id: str) -> Employee | None:
        _tid = self._get_active_tid()
        stmt = select(EmployeeORM).where(
            EmployeeORM.employee_code == employee_code,
            EmployeeORM.organization_id == organization_id,
        )
        if _tid is not None:
            stmt = stmt.where(EmployeeORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalars().first()
        return employee_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Employee]:
        _tid = self._get_active_tid()
        stmt = select(EmployeeORM).where(EmployeeORM.organization_id == organization_id)
        if _tid is not None:
            stmt = stmt.where(EmployeeORM.tenant_id == _tid)
        if active_only is not None:
            stmt = stmt.where(EmployeeORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(EmployeeORM.full_name.asc())).scalars().all()
        return [employee_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyEmployeeRepository",
]
