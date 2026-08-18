"""Project ORM rows."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, Enum as SAEnum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.modules.project_management.domain.enums import ProjectStatus
from src.infra.persistence.orm.base import Base
from src.infra.persistence.db.financial_numeric import (
    FinancialNumericKind,
    financial_numeric,
    financial_numeric_info,
)


class ProjectORM(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "id",
            name="uq_projects_tenant_organization_id",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    project_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="")
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus),
        default=ProjectStatus.PLANNED,
        nullable=False,
    )
    client_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    client_contact: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    site_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    client_party_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
    )
    manager_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_projects_tenant", ProjectORM.tenant_id)
Index("ux_projects_code", ProjectORM.project_code, unique=True)


class ProjectResourceORM(Base):
    __tablename__ = "project_resources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    hourly_rate: Mapped[Optional[Decimal]] = mapped_column(
        financial_numeric(FinancialNumericKind.RATE),
        info=financial_numeric_info(FinancialNumericKind.RATE),
        nullable=True,
    )
    currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    planned_hours: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.QUANTITY),
        info=financial_numeric_info(FinancialNumericKind.QUANTITY),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_project_resource_project", ProjectResourceORM.project_id)
Index("idx_project_resource_resource", ProjectResourceORM.resource_id)
Index(
    "ux_project_resource_project_resource",
    ProjectResourceORM.project_id,
    ProjectResourceORM.resource_id,
    unique=True,
)
