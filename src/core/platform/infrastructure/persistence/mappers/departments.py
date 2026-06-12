from __future__ import annotations

from src.core.platform.infrastructure.persistence.orm.departments import DepartmentORM
from src.core.platform.department.domain import Department


def department_to_orm(department: Department) -> DepartmentORM:
    return DepartmentORM(
        id=department.id,
        organization_id=department.organization_id,
        department_code=department.department_code,
        name=department.name,
        description=department.description or None,
        site_id=department.site_id,
        default_location_id=department.default_location_id,
        parent_department_id=department.parent_department_id,
        department_type=department.department_type or None,
        cost_center_code=department.cost_center_code or None,
        manager_employee_id=department.manager_employee_id,
        is_active=department.is_active,
        created_at=department.created_at,
        updated_at=department.updated_at,
        notes=department.notes or None,
        version=getattr(department, "version", 1),
    )


def department_from_orm(obj: DepartmentORM) -> Department:
    return Department(
        id=obj.id,
        organization_id=obj.organization_id,
        department_code=obj.department_code,
        name=obj.name,
        description=obj.description or "",
        site_id=obj.site_id,
        default_location_id=getattr(obj, "default_location_id", None),
        parent_department_id=obj.parent_department_id,
        department_type=obj.department_type or "",
        cost_center_code=obj.cost_center_code or "",
        manager_employee_id=obj.manager_employee_id,
        is_active=obj.is_active,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "department_from_orm",
    "department_to_orm",
]
