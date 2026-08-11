"""Canonical Project Finance forecast-version rows."""

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


class ProjectForecastORM(Base):
    __tablename__ = "project_finance_forecasts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name="fk_pf_forecasts_scoped_organization",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_forecasts_scoped_project",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "id",
            name="uq_pf_forecasts_scoped_id",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_pf_forecast_scope_project_id",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "revision",
            name="uq_pf_forecast_project_revision",
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'rejected', 'superseded')",
            name="ck_pf_forecasts_status",
        ),
        CheckConstraint(
            "generation_mode IN ('automatic', 'manual', 'hybrid')",
            name="ck_pf_forecasts_generation_mode",
        ),
        CheckConstraint("revision >= 1", name="ck_pf_forecasts_revision"),
        CheckConstraint("version >= 1", name="ck_pf_forecasts_version"),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    generation_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    submitted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(String, nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    submission_notes: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    approval_notes: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    rejection_notes: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("idx_pf_forecasts_scope", ProjectForecastORM.tenant_id, ProjectForecastORM.organization_id)
Index("idx_pf_forecasts_project", ProjectForecastORM.project_id)
Index(
    "uq_pf_forecasts_one_approved_per_project",
    ProjectForecastORM.tenant_id,
    ProjectForecastORM.organization_id,
    ProjectForecastORM.project_id,
    unique=True,
    postgresql_where=(ProjectForecastORM.status == "approved"),
    sqlite_where=(ProjectForecastORM.status == "approved"),
)
Index(
    "uq_pf_forecasts_one_open_per_project",
    ProjectForecastORM.tenant_id,
    ProjectForecastORM.organization_id,
    ProjectForecastORM.project_id,
    unique=True,
    postgresql_where=ProjectForecastORM.status.in_(["draft", "submitted"]),
    sqlite_where=ProjectForecastORM.status.in_(["draft", "submitted"]),
)


class ForecastLineORM(Base):
    __tablename__ = "project_finance_forecast_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "forecast_id"],
            [
                "project_finance_forecasts.tenant_id",
                "project_finance_forecasts.organization_id",
                "project_finance_forecasts.project_id",
                "project_finance_forecasts.id",
            ],
            name="fk_pf_forecast_lines_scoped_forecast",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_forecast_lines_scoped_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_forecast_lines_scoped_cost_code",
            ondelete="RESTRICT",
        ),
        CheckConstraint("amount >= 0", name="ck_pf_forecast_lines_amount"),
        CheckConstraint("version >= 1", name="ck_pf_forecast_lines_version"),
        CheckConstraint(
            "source_kind IN ('automatic', 'manual')",
            name="ck_pf_forecast_lines_source_kind",
        ),
        CheckConstraint(
            "source_type IN ('remaining_plan', 'open_commitment', 'risk', 'manual_estimate')",
            name="ck_pf_forecast_lines_source_type",
        ),
        CheckConstraint(
            "(period_start IS NULL AND period_end IS NULL) OR "
            "(period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start)",
            name="ck_pf_forecast_lines_period",
        ),
        CheckConstraint(
            "(source_kind = 'manual' AND source_type = 'manual_estimate') OR "
            "(source_kind = 'manual' AND source_type = 'risk' "
            "AND source_reference_type IS NOT NULL AND source_reference_id IS NOT NULL "
            "AND source_snapshot_at IS NOT NULL) OR "
            "(source_kind = 'automatic' AND source_type <> 'manual_estimate' "
            "AND source_reference_type IS NOT NULL AND source_reference_id IS NOT NULL "
            "AND source_snapshot_at IS NOT NULL)",
            name="ck_pf_forecast_lines_source_metadata",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    forecast_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    cost_code_id: Mapped[str] = mapped_column(String, nullable=False)
    task_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=True
    )
    description: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_reference_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_snapshot_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("idx_pf_forecast_lines_scope", ForecastLineORM.tenant_id, ForecastLineORM.organization_id)
Index("idx_pf_forecast_lines_forecast", ForecastLineORM.forecast_id)
Index("idx_pf_forecast_lines_cost_code", ForecastLineORM.cost_code_id)
Index("idx_pf_forecast_lines_task", ForecastLineORM.task_id)
Index(
    "idx_pf_forecast_lines_source",
    ForecastLineORM.source_reference_type,
    ForecastLineORM.source_reference_id,
)


class ForecastSourceDecisionORM(Base):
    __tablename__ = "project_finance_forecast_source_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "forecast_id"],
            [
                "project_finance_forecasts.tenant_id",
                "project_finance_forecasts.organization_id",
                "project_finance_forecasts.project_id",
                "project_finance_forecasts.id",
            ],
            name="fk_pf_forecast_decisions_scoped_forecast",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_pf_forecast_decisions_scoped_cost_code",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "action IN ('included', 'offset', 'excluded')",
            name="ck_pf_forecast_decisions_action",
        ),
        CheckConstraint(
            "reason IN ('remaining_plan', 'open_commitment', 'posted_actual_offset', "
            "'actual_credit', 'reversed_actual', "
            "'manual_override', 'risk_contingency', "
            "'no_remaining_amount', 'closed_or_cancelled', 'after_as_of')",
            name="ck_pf_forecast_decisions_reason",
        ),
        CheckConstraint(
            "source_type IN ('remaining_plan', 'open_commitment', 'risk', 'manual_estimate', "
            "'posted_actual')",
            name="ck_pf_forecast_decisions_source_type",
        ),
        CheckConstraint(
            "source_amount >= 0 AND included_amount >= 0 AND excluded_amount >= 0",
            name="ck_pf_forecast_decisions_amounts",
        ),
        CheckConstraint(
            "included_amount + excluded_amount = source_amount",
            name="ck_pf_forecast_decisions_reconciled",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    forecast_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    cost_code_id: Mapped[str] = mapped_column(String, nullable=False)
    task_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_reference_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    source_amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    included_amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    excluded_amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    source_snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "idx_pf_forecast_decisions_scope",
    ForecastSourceDecisionORM.tenant_id,
    ForecastSourceDecisionORM.organization_id,
)
Index("idx_pf_forecast_decisions_forecast", ForecastSourceDecisionORM.forecast_id)
Index(
    "idx_pf_forecast_decisions_source",
    ForecastSourceDecisionORM.source_reference_type,
    ForecastSourceDecisionORM.source_reference_id,
)


__all__ = ["ForecastLineORM", "ForecastSourceDecisionORM", "ProjectForecastORM"]
