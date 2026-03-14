from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.platform.common.interfaces import EmployeeRepository, OrganizationRepository
from core.platform.common.models import Employee, Organization
from infra.platform.db.models import EmployeeORM, OrganizationORM
from infra.platform.db.optimistic import update_with_version_check
from infra.platform.db.org.mapper import (
    employee_from_orm,
    employee_to_orm,
    organization_from_orm,
    organization_to_orm,
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
                "department": (employee.department or None),
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


__all__ = ["SqlAlchemyEmployeeRepository", "SqlAlchemyOrganizationRepository"]
