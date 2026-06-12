from __future__ import annotations

from src.core.platform.infrastructure.persistence.orm.employee import EmployeeORM
from src.core.platform.employee.domain import Employee


def employee_to_orm(employee: Employee) -> EmployeeORM:
    return EmployeeORM(
        id=employee.id,
        employee_code=employee.employee_code,
        full_name=employee.full_name,
        department_id=employee.department_id,
        department=(employee.department or None),
        site_id=employee.site_id,
        site_name=(employee.site_name or None),
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
        department_id=getattr(obj, "department_id", None),
        department=obj.department or "",
        site_id=getattr(obj, "site_id", None),
        site_name=getattr(obj, "site_name", None) or "",
        title=obj.title or "",
        employment_type=obj.employment_type,
        email=obj.email,
        phone=obj.phone,
        is_active=obj.is_active,
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "employee_from_orm",
    "employee_to_orm",
]
