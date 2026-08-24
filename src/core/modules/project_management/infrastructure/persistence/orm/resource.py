"""Resource ORM rows."""

from __future__ import annotations

from typing import Optional
from decimal import Decimal

from sqlalchemy import Boolean, Enum as SAEnum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.modules.project_management.domain.enums import CostType, ResourceKind, WorkerType
from src.infra.persistence.orm.base import Base
from src.infra.persistence.db.financial_numeric import (
    FinancialNumericKind,
    financial_numeric,
    financial_numeric_info,
)


class ResourceORM(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resource_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[ResourceKind] = mapped_column(
        SAEnum(ResourceKind),
        nullable=False,
        default=ResourceKind.PERSON,
        server_default=ResourceKind.PERSON.value,
    )
    role: Mapped[str] = mapped_column(String, default="")
    hourly_rate: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.RATE),
        info=financial_numeric_info(FinancialNumericKind.RATE),
        default=Decimal("0"),
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Macro capacity override used by portfolio planning and dashboard alerts.
    # For per-day scheduling capacity, the enterprise CalendarResolver derives it
    # from calendar_working_rules + exceptions. These two models are complementary:
    # capacity_percent = portfolio-level availability fraction (e.g. 50% = half-time resource),
    # enterprise daily capacity = actual hours available after rules/exceptions.
    capacity_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
        server_default="100.0",
    )
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cost_type: Mapped[CostType] = mapped_column(
        SAEnum(CostType),
        default=CostType.LABOR,
        nullable=False,
    )
    currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    worker_type: Mapped[WorkerType] = mapped_column(
        SAEnum(WorkerType),
        nullable=False,
        default=WorkerType.EXTERNAL,
        server_default=WorkerType.EXTERNAL.value,
    )
    employee_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    department_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    site_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_resources_tenant", ResourceORM.tenant_id)
Index("idx_resources_employee", ResourceORM.employee_id)
Index(
    "ux_resources_scope_code",
    ResourceORM.tenant_id,
    ResourceORM.organization_id,
    ResourceORM.resource_code,
    unique=True,
)
Index(
    "ux_resources_scope_employee",
    ResourceORM.tenant_id,
    ResourceORM.organization_id,
    ResourceORM.employee_id,
    unique=True,
    sqlite_where=ResourceORM.employee_id.is_not(None),
    postgresql_where=ResourceORM.employee_id.is_not(None),
)
Index("idx_resources_scope", ResourceORM.tenant_id, ResourceORM.organization_id)
Index("idx_resources_organization", ResourceORM.organization_id)
Index("idx_resources_department", ResourceORM.department_id)
Index("idx_resources_site", ResourceORM.site_id)
