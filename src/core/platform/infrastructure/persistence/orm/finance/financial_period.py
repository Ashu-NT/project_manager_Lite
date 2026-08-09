"""Persistence model for organization financial periods."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class FinancialPeriodORM(Base):
    __tablename__ = "financial_periods"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_financial_periods_scoped_organization",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "id",
            name="uq_financial_periods_scoped_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "code",
            name="uq_financial_periods_scoped_code",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "fiscal_year",
            "period_number",
            name="uq_financial_periods_year_number",
        ),
        CheckConstraint(
            "status IN ('open', 'closed', 'locked')",
            name="ck_financial_periods_status",
        ),
        CheckConstraint(
            "length(code) >= 1 AND length(code) <= 32",
            name="ck_financial_periods_code_length",
        ),
        CheckConstraint(
            "length(name) >= 1 AND length(name) <= 128",
            name="ck_financial_periods_name_length",
        ),
        CheckConstraint(
            "(status = 'open' AND closed_by IS NULL AND closed_at IS NULL "
            "AND locked_by IS NULL AND locked_at IS NULL) OR "
            "(status = 'closed' AND closed_by IS NOT NULL AND closed_at IS NOT NULL "
            "AND locked_by IS NULL AND locked_at IS NULL) OR "
            "(status = 'locked' AND closed_by IS NOT NULL AND closed_at IS NOT NULL "
            "AND locked_by IS NOT NULL AND locked_at IS NOT NULL)",
            name="ck_financial_periods_lifecycle_metadata",
        ),
        CheckConstraint(
            "end_date >= start_date",
            name="ck_financial_periods_date_range",
        ),
        CheckConstraint(
            "fiscal_year >= 1 AND fiscal_year <= 9999",
            name="ck_financial_periods_fiscal_year",
        ),
        CheckConstraint(
            "period_number >= 1 AND period_number <= 999",
            name="ck_financial_periods_period_number",
        ),
        CheckConstraint("version >= 1", name="ck_financial_periods_version"),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="open")
    closed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String, nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("idx_financial_periods_scope", FinancialPeriodORM.tenant_id, FinancialPeriodORM.organization_id)
Index(
    "idx_financial_periods_dates",
    FinancialPeriodORM.tenant_id,
    FinancialPeriodORM.organization_id,
    FinancialPeriodORM.start_date,
    FinancialPeriodORM.end_date,
)
Index(
    "idx_financial_periods_status",
    FinancialPeriodORM.tenant_id,
    FinancialPeriodORM.organization_id,
    FinancialPeriodORM.status,
)


__all__ = ["FinancialPeriodORM"]
