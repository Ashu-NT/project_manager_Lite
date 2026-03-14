from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.platform.common.interfaces import EmployeeRepository
from core.platform.common.models import Employee
from infra.platform.db.models import EmployeeORM
from infra.platform.db.optimistic import update_with_version_check
from infra.platform.db.org.mapper import employee_from_orm, employee_to_orm


class SqlAlchemyEmployeeRepository(EmployeeRepository):
    def __init__(self, session: Session):
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
                "department": (employee.department or None),
                "title": (employee.title or None),
                "employment_type": employee.employment_type,
                "email": employee.email,
                "phone": employee.phone,
                "is_active": employee.is_active,
            },
            not_found_message="Employee not found.",
            stale_message="Employee was updated by another user.",
        )

    def get(self, employee_id: str) -> Optional[Employee]:
        obj = self.session.get(EmployeeORM, employee_id)
        return employee_from_orm(obj) if obj else None

    def get_by_code(self, employee_code: str) -> Optional[Employee]:
        stmt = select(EmployeeORM).where(EmployeeORM.employee_code == employee_code)
        obj = self.session.execute(stmt).scalars().first()
        return employee_from_orm(obj) if obj else None

    def list_all(self, *, active_only: bool | None = None) -> List[Employee]:
        stmt = select(EmployeeORM)
        if active_only is not None:
            stmt = stmt.where(EmployeeORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(EmployeeORM.full_name.asc())).scalars().all()
        return [employee_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyEmployeeRepository"]
