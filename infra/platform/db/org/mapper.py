from __future__ import annotations

from core.platform.common.models import Employee, Organization, Site
from infra.platform.db.models import EmployeeORM, OrganizationORM, SiteORM


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
        display_name=site.display_name,
        is_active=site.is_active,
        version=getattr(site, "version", 1),
    )


def site_from_orm(obj: SiteORM) -> Site:
    return Site(
        id=obj.id,
        organization_id=obj.organization_id,
        site_code=obj.site_code,
        display_name=obj.display_name,
        is_active=obj.is_active,
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "employee_from_orm",
    "employee_to_orm",
    "organization_from_orm",
    "organization_to_orm",
    "site_from_orm",
    "site_to_orm",
]
