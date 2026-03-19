from __future__ import annotations

from core.platform.common.models import Department, Employee, Organization, Site
from infra.platform.db.models import DepartmentORM, EmployeeORM, OrganizationORM, SiteORM


def employee_to_orm(employee: Employee) -> EmployeeORM:
    return EmployeeORM(
        id=employee.id,
        employee_code=employee.employee_code,
        full_name=employee.full_name,
        department=(employee.department or None),
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
        department=obj.department or "",
        site_name=getattr(obj, "site_name", None) or "",
        title=obj.title or "",
        employment_type=obj.employment_type,
        email=obj.email,
        phone=obj.phone,
        is_active=obj.is_active,
        version=getattr(obj, "version", 1),
    )


def organization_to_orm(organization: Organization) -> OrganizationORM:
    return OrganizationORM(
        id=organization.id,
        organization_code=organization.organization_code,
        display_name=organization.display_name,
        timezone_name=organization.timezone_name,
        base_currency=organization.base_currency,
        is_active=organization.is_active,
        version=getattr(organization, "version", 1),
    )


def organization_from_orm(obj: OrganizationORM) -> Organization:
    return Organization(
        id=obj.id,
        organization_code=obj.organization_code,
        display_name=obj.display_name,
        timezone_name=obj.timezone_name,
        base_currency=obj.base_currency,
        is_active=obj.is_active,
        version=getattr(obj, "version", 1),
    )


def site_to_orm(site: Site) -> SiteORM:
    return SiteORM(
        id=site.id,
        organization_id=site.organization_id,
        site_code=site.site_code,
        name=site.name,
        description=site.description or None,
        country=site.country or None,
        region=site.region or None,
        city=site.city or None,
        address_line_1=site.address_line_1 or None,
        address_line_2=site.address_line_2 or None,
        postal_code=site.postal_code or None,
        timezone=site.timezone or None,
        currency_code=site.currency_code or None,
        site_type=site.site_type or None,
        status=site.status or None,
        default_calendar_id=site.default_calendar_id or None,
        default_language=site.default_language or None,
        is_active=site.is_active,
        opened_at=site.opened_at,
        closed_at=site.closed_at,
        created_at=site.created_at,
        updated_at=site.updated_at,
        notes=site.notes or None,
        version=getattr(site, "version", 1),
    )


def site_from_orm(obj: SiteORM) -> Site:
    return Site(
        id=obj.id,
        organization_id=obj.organization_id,
        site_code=obj.site_code,
        name=obj.name,
        description=obj.description or "",
        country=obj.country or "",
        region=obj.region or "",
        city=obj.city or "",
        address_line_1=obj.address_line_1 or "",
        address_line_2=obj.address_line_2 or "",
        postal_code=obj.postal_code or "",
        timezone=obj.timezone or "",
        currency_code=obj.currency_code or "",
        site_type=obj.site_type or "",
        status=obj.status or "",
        default_calendar_id=obj.default_calendar_id or "",
        default_language=obj.default_language or "",
        is_active=obj.is_active,
        opened_at=obj.opened_at,
        closed_at=obj.closed_at,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


def department_to_orm(department: Department) -> DepartmentORM:
    return DepartmentORM(
        id=department.id,
        organization_id=department.organization_id,
        department_code=department.department_code,
        name=department.name,
        description=department.description or None,
        site_id=department.site_id,
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
    "employee_from_orm",
    "employee_to_orm",
    "organization_from_orm",
    "organization_to_orm",
    "site_from_orm",
    "site_to_orm",
]
