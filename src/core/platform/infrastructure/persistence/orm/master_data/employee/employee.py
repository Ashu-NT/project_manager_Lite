"""Platform employee ORM model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.core.platform.domain.master_data.employee import (
    EmployeeLifecycleStatus,
    EmploymentType,
)
from src.infra.persistence.orm.base import Base


class EmployeeORM(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    # Unique per-organization (see idx_employees_org_code below), never
    # globally across every organization/tenant -- an Employee Number is
    # business identity scoped to the org that assigned it, not a
    # tenant-wide or database-wide primary key.
    employee_code: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    # Required: every real construction path already resolves the active
    # organization before persisting an Employee -- this makes that
    # operational reality a precise, enforced invariant.
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=False,
    )
    # Required: every Employee belongs to exactly one Department. ondelete
    # stays SET NULL at the DB level for now (unchanged from before this
    # column became required) -- Departments are never hard-deleted in this
    # app (lifecycle is Active/Inactive only), so it never actually fires.
    department_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=False,
    )
    department: Mapped[str | None] = mapped_column(String(256), nullable=True)
    site_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
    )
    site_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        SAEnum(EmploymentType),
        nullable=False,
        default=EmploymentType.FULL_TIME,
        server_default=EmploymentType.FULL_TIME.value,
    )
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Sole lifecycle source of truth -- never a second persisted `is_active`
    # boolean alongside it (see EmployeeLifecycleStatus.is_active, a
    # computed domain property, not a column).
    status: Mapped[EmployeeLifecycleStatus] = mapped_column(
        # values_callable is required here: the migration backfilled this
        # column (a plain VARCHAR, not a native SQL enum type) with the
        # enum's lowercase VALUES ("active"/"inactive"), matching every
        # other consumer's own use of `.value` (audit trails, EmployeeDto
        # serialization) -- SQLAlchemy's Enum type defaults to storing/
        # reading by member NAME ("ACTIVE"/"INACTIVE") instead, which would
        # silently mismatch the real persisted data.
        SAEnum(EmployeeLifecycleStatus, values_callable=lambda enum_cls: [member.value for member in enum_cls]),
        nullable=False,
        default=EmployeeLifecycleStatus.ACTIVE,
        server_default=EmployeeLifecycleStatus.ACTIVE.value,
    )
    # Optional one-to-one with User: unique so one User cannot be linked to
    # more than one Employee (partial index -- multiple NULLs are fine).
    # Employee stays the owning reference; User carries no reciprocal FK.
    user_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_employees_tenant", EmployeeORM.tenant_id)
Index("idx_employees_organization", EmployeeORM.organization_id)
Index("idx_employees_department", EmployeeORM.department_id)
Index("idx_employees_site", EmployeeORM.site_id)
# Unique per-organization, not globally -- see the employee_code column
# comment above.
Index("idx_employees_org_code", EmployeeORM.organization_id, EmployeeORM.employee_code, unique=True)
Index("idx_employees_status", EmployeeORM.status)
Index("idx_employees_user", EmployeeORM.user_id, unique=True, sqlite_where=EmployeeORM.user_id.isnot(None))
