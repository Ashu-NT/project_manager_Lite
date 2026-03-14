from __future__ import annotations

from core.platform.common.models import Employee
from infra.platform.db.models import EmployeeORM


def employee_to_orm(employee: Employee) -> EmployeeORM:
    return EmployeeORM(
        id=employee.id,
        employee_code=employee.employee_code,
        full_name=employee.full_name,
        department=(employee.department or None),
        title=(employee.title or None),
        employment_type=employee.employment_type,
        email=employee.email,
        phone=employee.phone,
        is_active=employee.is_active,
        version=getattr(employee, "version", 1),
    )


def employee_from_orm(obj: EmployeeORM) -> Employee:
    return Employee(
        id=obj.id,
        employee_code=obj.employee_code,
        full_name=obj.full_name,
        department=obj.department or "",
        title=obj.title or "",
        employment_type=obj.employment_type,
        email=obj.email,
        phone=obj.phone,
        is_active=obj.is_active,
        version=getattr(obj, "version", 1),
    )


__all__ = ["employee_from_orm", "employee_to_orm"]
