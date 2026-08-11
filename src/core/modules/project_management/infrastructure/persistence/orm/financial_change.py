"""Canonical Project Finance change-order rows."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

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

from src.infra.persistence.db.financial_numeric import (
    FinancialNumericKind,
    financial_numeric,
    financial_numeric_info,
)
from src.infra.persistence.orm.base import Base


class FinancialChangeRequestORM(Base):
    __tablename__ = "project_finance_change_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_changes_scoped_organization",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_changes_scoped_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "base_budget_id"],
            [
                "project_finance_budgets.tenant_id",
                "project_finance_budgets.organization_id",
                "project_finance_budgets.project_id",
                "project_finance_budgets.id",
            ],
            name="fk_pf_changes_scoped_base_budget",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "base_forecast_id"],
            [
                "project_finance_forecasts.tenant_id",
                "project_finance_forecasts.organization_id",
                "project_finance_forecasts.project_id",
                "project_finance_forecasts.id",
            ],
            name="fk_pf_changes_scoped_base_forecast",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "applied_budget_id"],
            [
                "project_finance_budgets.tenant_id",
                "project_finance_budgets.organization_id",
                "project_finance_budgets.project_id",
                "project_finance_budgets.id",
            ],
            name="fk_pf_changes_scoped_applied_budget",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "applied_forecast_id"],
            [
                "project_finance_forecasts.tenant_id",
                "project_finance_forecasts.organization_id",
                "project_finance_forecasts.project_id",
                "project_finance_forecasts.id",
            ],
            name="fk_pf_changes_scoped_applied_forecast",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_pf_change_scope_project_id",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "revision",
            name="uq_pf_change_project_revision",
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'applied', 'rejected')",
            name="ck_pf_changes_status",
        ),
        CheckConstraint("revision >= 1", name="ck_pf_changes_revision"),
        CheckConstraint("version >= 1", name="ck_pf_changes_version"),
        CheckConstraint(
            "(base_budget_id IS NULL AND base_budget_revision IS NULL) OR "
            "(base_budget_id IS NOT NULL AND base_budget_revision >= 1)",
            name="ck_pf_changes_base_budget_pair",
        ),
        CheckConstraint(
            "(base_forecast_id IS NULL AND base_forecast_revision IS NULL) OR "
            "(base_forecast_id IS NOT NULL AND base_forecast_revision >= 1)",
            name="ck_pf_changes_base_forecast_pair",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="draft")
    base_budget_id: Mapped[str | None] = mapped_column(String, nullable=True)
    base_budget_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_forecast_id: Mapped[str | None] = mapped_column(String, nullable=True)
    base_forecast_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approval_request_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("approval_requests.id", ondelete="RESTRICT"), nullable=True
    )
    applied_budget_id: Mapped[str | None] = mapped_column(String, nullable=True)
    applied_forecast_id: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by: Mapped[str | None] = mapped_column(String, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_notes: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_pf_changes_scope",
    FinancialChangeRequestORM.tenant_id,
    FinancialChangeRequestORM.organization_id,
)
Index("idx_pf_changes_project", FinancialChangeRequestORM.project_id)
Index("idx_pf_changes_status", FinancialChangeRequestORM.status)
Index("idx_pf_changes_approval", FinancialChangeRequestORM.approval_request_id)


class FinancialChangeImpactORM(Base):
    __tablename__ = "project_finance_change_impacts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "change_request_id"],
            [
                "project_finance_change_requests.tenant_id",
                "project_finance_change_requests.organization_id",
                "project_finance_change_requests.project_id",
                "project_finance_change_requests.id",
            ],
            name="fk_pf_change_impacts_scoped_request",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_change_impacts_scoped_cost_code",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "impact_type IN ('budget', 'forecast', 'contract', 'schedule')",
            name="ck_pf_change_impacts_type",
        ),
        CheckConstraint(
            "impact_type NOT IN ('budget', 'forecast', 'contract') OR "
            "(amount <> 0 AND currency_code IS NOT NULL AND cost_code_id IS NOT NULL)",
            name="ck_pf_change_impacts_monetary_shape",
        ),
        CheckConstraint(
            "impact_type <> 'contract' OR "
            "(source_reference_type IS NOT NULL AND source_reference_id IS NOT NULL)",
            name="ck_pf_change_impacts_contract_source",
        ),
        CheckConstraint(
            "impact_type <> 'schedule' OR "
            "(task_id IS NOT NULL AND "
            "(schedule_start IS NOT NULL OR schedule_finish IS NOT NULL OR planned_hours_delta <> 0))",
            name="ck_pf_change_impacts_schedule_shape",
        ),
        CheckConstraint(
            "schedule_start IS NULL OR schedule_finish IS NULL OR schedule_finish >= schedule_start",
            name="ck_pf_change_impacts_schedule_period",
        ),
        CheckConstraint(
            "amount >= 0 OR target_line_id IS NOT NULL OR "
            "impact_type NOT IN ('budget', 'forecast')",
            name="ck_pf_change_impacts_negative_target",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    change_request_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    impact_type: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        default=Decimal("0"),
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    currency_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    cost_code_id: Mapped[str | None] = mapped_column(String, nullable=True)
    task_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=True
    )
    target_line_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_reference_id: Mapped[str | None] = mapped_column(String, nullable=True)
    schedule_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    schedule_finish: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_hours_delta: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.QUANTITY),
        nullable=False,
        default=Decimal("0"),
        info=financial_numeric_info(FinancialNumericKind.QUANTITY),
    )
    applied_line_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_pf_change_impacts_scope",
    FinancialChangeImpactORM.tenant_id,
    FinancialChangeImpactORM.organization_id,
)
Index("idx_pf_change_impacts_request", FinancialChangeImpactORM.change_request_id)
Index("idx_pf_change_impacts_target", FinancialChangeImpactORM.target_line_id)
Index(
    "idx_pf_change_impacts_source",
    FinancialChangeImpactORM.source_reference_type,
    FinancialChangeImpactORM.source_reference_id,
)


__all__ = ["FinancialChangeImpactORM", "FinancialChangeRequestORM"]
