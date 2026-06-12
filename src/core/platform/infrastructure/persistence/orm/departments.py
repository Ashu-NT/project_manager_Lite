"""Platform department ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class DepartmentORM(Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("organization_id", "department_code", name="ux_departments_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
    )
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


Index("idx_departments_tenant", DepartmentORM.tenant_id)
Index("idx_departments_organization", DepartmentORM.organization_id)
Index("idx_departments_active", DepartmentORM.organization_id, DepartmentORM.is_active)
Index("idx_departments_site", DepartmentORM.site_id)
Index("idx_departments_default_location", DepartmentORM.default_location_id)
