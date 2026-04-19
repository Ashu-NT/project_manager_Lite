from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.org.contracts import (
    DepartmentRepository,
    EmployeeRepository,
    OrganizationRepository,
    SiteRepository,
)
from src.core.platform.org.domain import Department, Employee, Organization, Site
from src.core.platform.infrastructure.persistence.orm.models import DepartmentORM, EmployeeORM, OrganizationORM, SiteORM
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.platform.infrastructure.persistence.org.mapper import (
    department_from_orm,
    department_to_orm,
    employee_from_orm,
    employee_to_orm,
    organization_from_orm,
    organization_to_orm,
    site_from_orm,
    site_to_orm,
)


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


class SqlAlchemyOrganizationRepository(OrganizationRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, organization: Organization) -> None:
        self.session.add(organization_to_orm(organization))

    def update(self, organization: Organization) -> None:
        organization.version = update_with_version_check(
            self.session,
            OrganizationORM,
            organization.id,
            getattr(organization, "version", 1),
            {
                "organization_code": organization.organization_code,
                "display_name": organization.display_name,
                "timezone_name": organization.timezone_name,
                "base_currency": organization.base_currency,
                "is_active": organization.is_active,
            },
            not_found_message="Organization not found.",
            stale_message="Organization was updated by another user.",
        )

    def get(self, organization_id: str) -> Optional[Organization]:
        obj = self.session.get(OrganizationORM, organization_id)
        return organization_from_orm(obj) if obj else None

    def get_by_code(self, organization_code: str) -> Optional[Organization]:
        stmt = select(OrganizationORM).where(OrganizationORM.organization_code == organization_code)
        obj = self.session.execute(stmt).scalars().first()
        return organization_from_orm(obj) if obj else None

    def get_active(self) -> Optional[Organization]:
        stmt = select(OrganizationORM).where(OrganizationORM.is_active.is_(True))
        obj = self.session.execute(stmt.order_by(OrganizationORM.display_name.asc())).scalars().first()
        return organization_from_orm(obj) if obj else None

    def list_all(self, *, active_only: bool | None = None) -> List[Organization]:
        stmt = select(OrganizationORM)
        if active_only is not None:
            stmt = stmt.where(OrganizationORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(OrganizationORM.display_name.asc())).scalars().all()
        return [organization_from_orm(row) for row in rows]


class SqlAlchemySiteRepository(SiteRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, site: Site) -> None:
        self.session.add(site_to_orm(site))

    def update(self, site: Site) -> None:
        site.version = update_with_version_check(
            self.session,
            SiteORM,
            site.id,
            getattr(site, "version", 1),
            {
                "site_code": site.site_code,
                "name": site.name,
                "description": site.description or None,
                "country": site.country or None,
                "region": site.region or None,
                "city": site.city or None,
                "address_line_1": site.address_line_1 or None,
                "address_line_2": site.address_line_2 or None,
                "postal_code": site.postal_code or None,
                "timezone": site.timezone or None,
                "currency_code": site.currency_code or None,
                "site_type": site.site_type or None,
                "status": site.status or None,
                "default_calendar_id": site.default_calendar_id or None,
                "default_language": site.default_language or None,
                "is_active": site.is_active,
                "opened_at": site.opened_at,
                "closed_at": site.closed_at,
                "created_at": site.created_at,
                "updated_at": site.updated_at,
                "notes": site.notes or None,
            },
            not_found_message="Site not found.",
            stale_message="Site was updated by another user.",
        )

    def get(self, site_id: str) -> Optional[Site]:
        obj = self.session.get(SiteORM, site_id)
        return site_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, site_code: str) -> Optional[Site]:
        stmt = select(SiteORM).where(
            SiteORM.organization_id == organization_id,
            SiteORM.site_code == site_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return site_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> List[Site]:
        stmt = select(SiteORM).where(SiteORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(SiteORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(SiteORM.name.asc())).scalars().all()
        return [site_from_orm(row) for row in rows]


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
    "SqlAlchemyEmployeeRepository",
    "SqlAlchemyOrganizationRepository",
    "SqlAlchemySiteRepository",
]
