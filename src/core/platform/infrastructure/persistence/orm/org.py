"""Platform ORM models for organization data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy import (
    Boolean,
    Date,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.platform.org.domain import EmploymentType
from src.core.platform.time.domain import TimesheetPeriodStatus
from src.infra.persistence.orm.base import Base

class EmployeeORM(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    department_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    department: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    site_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
    )
    site_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        SAEnum(EmploymentType),
        nullable=False,
        default=EmploymentType.FULL_TIME,
        server_default=EmploymentType.FULL_TIME.value,
    )
    email: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_employees_department", EmployeeORM.department_id)
Index("idx_employees_site", EmployeeORM.site_id)
Index("idx_employees_code", EmployeeORM.employee_code, unique=True)
Index("idx_employees_active", EmployeeORM.is_active)


class OrganizationORM(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    timezone_name: Mapped[str] = mapped_column(String(128), nullable=False, default="UTC", server_default="UTC")
    base_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR", server_default="EUR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_organizations_code", OrganizationORM.organization_code, unique=True)
Index("idx_organizations_active", OrganizationORM.is_active)


class SiteORM(Base):
    __tablename__ = "sites"
    __table_args__ = (
        UniqueConstraint("organization_id", "site_code", name="ux_sites_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    site_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    address_line_1: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    address_line_2: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    site_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    default_calendar_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    default_language: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_sites_organization", SiteORM.organization_id)
Index("idx_sites_active", SiteORM.organization_id, SiteORM.is_active)


class DepartmentORM(Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("organization_id", "department_code", name="ux_departments_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    site_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
    )
    default_location_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_department_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    cost_center_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    manager_employee_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_departments_organization", DepartmentORM.organization_id)
Index("idx_departments_active", DepartmentORM.organization_id, DepartmentORM.is_active)
Index("idx_departments_site", DepartmentORM.site_id)
Index("idx_departments_default_location", DepartmentORM.default_location_id)
