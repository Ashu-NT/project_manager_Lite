"""Canonical Project Finance actual-cost ledger rows."""

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


class ProjectCostEntryORM(Base):
    __tablename__ = "project_cost_entries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_project_cost_entries_scoped_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_project_cost_entries_scoped_cost_code",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            name="fk_project_cost_entries_project_task",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "financial_period_id"],
            [
                "financial_periods.tenant_id",
                "financial_periods.organization_id",
                "financial_periods.id",
            ],
            name="fk_project_cost_entries_scoped_period",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "reverses_entry_id"],
            [
                "project_cost_entries.tenant_id",
                "project_cost_entries.organization_id",
                "project_cost_entries.project_id",
                "project_cost_entries.id",
            ],
            name="fk_project_cost_entries_scoped_reversal",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "reversed_by_entry_id"],
            [
                "project_cost_entries.tenant_id",
                "project_cost_entries.organization_id",
                "project_cost_entries.project_id",
                "project_cost_entries.id",
            ],
            name="fk_project_cost_entries_scoped_reversed_by",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "project_id",
            "id",
            name="uq_project_cost_entries_scoped_project_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "organization_id",
            "idempotency_key",
            name="uq_project_cost_entries_idempotency",
        ),
        CheckConstraint(
            "entry_kind IN ('actual', 'adjustment', 'reversal')",
            name="ck_project_cost_entries_kind",
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'posted', 'reversed')",
            name="ck_project_cost_entries_status",
        ),
        CheckConstraint(
            "(entry_kind = 'actual' AND amount > 0 AND reverses_entry_id IS NULL) OR "
            "(entry_kind = 'adjustment' AND amount <> 0 AND reverses_entry_id IS NULL) OR "
            "(entry_kind = 'reversal' AND amount < 0 AND reverses_entry_id IS NOT NULL)",
            name="ck_project_cost_entries_sign_and_reversal",
        ),
        CheckConstraint(
            "(status IN ('posted', 'reversed') AND base_amount IS NOT NULL "
            "AND base_currency_code IS NOT NULL AND exchange_rate IS NOT NULL "
            "AND exchange_rate_date IS NOT NULL AND exchange_rate_source IS NOT NULL "
            "AND exchange_rate_captured_at IS NOT NULL AND posting_date IS NOT NULL "
            "AND financial_period_id IS NOT NULL AND posted_by IS NOT NULL AND posted_at IS NOT NULL) "
            "OR (status IN ('draft', 'submitted', 'approved') AND base_amount IS NULL "
            "AND base_currency_code IS NULL AND exchange_rate IS NULL "
            "AND exchange_rate_date IS NULL AND exchange_rate_source IS NULL "
            "AND exchange_rate_captured_at IS NULL AND posting_date IS NULL "
            "AND financial_period_id IS NULL AND posted_by IS NULL AND posted_at IS NULL)",
            name="ck_project_cost_entries_posting_snapshot",
        ),
        CheckConstraint(
            "exchange_rate IS NULL OR exchange_rate > 0",
            name="ck_project_cost_entries_exchange_rate",
        ),
        CheckConstraint(
            "base_amount IS NULL OR (base_amount <> 0 AND amount * base_amount > 0)",
            name="ck_project_cost_entries_base_sign",
        ),
        CheckConstraint("version >= 1", name="ck_project_cost_entries_version"),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    entry_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )
    amount: Mapped[Decimal] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=False,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    base_amount: Mapped[Decimal | None] = mapped_column(
        financial_numeric(FinancialNumericKind.MONEY),
        nullable=True,
        info=financial_numeric_info(FinancialNumericKind.MONEY),
    )
    base_currency_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    exchange_rate: Mapped[Decimal | None] = mapped_column(
        financial_numeric(FinancialNumericKind.EXCHANGE_RATE),
        nullable=True,
        info=financial_numeric_info(FinancialNumericKind.EXCHANGE_RATE),
    )
    exchange_rate_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exchange_rate_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    exchange_rate_captured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    posting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    financial_period_id: Mapped[str | None] = mapped_column(String, nullable=True)
    cost_code_id: Mapped[str] = mapped_column(String, nullable=False)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    resource_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("resources.id", ondelete="RESTRICT"), nullable=True
    )
    source_module: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_line_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    posting_purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    reverses_entry_id: Mapped[str | None] = mapped_column(String, nullable=True)
    reversed_by_entry_id: Mapped[str | None] = mapped_column(String, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_notes: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    posted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index(
    "idx_project_cost_entries_scope_project",
    ProjectCostEntryORM.tenant_id,
    ProjectCostEntryORM.organization_id,
    ProjectCostEntryORM.project_id,
)
Index(
    "idx_project_cost_entries_project_posting",
    ProjectCostEntryORM.project_id,
    ProjectCostEntryORM.posting_date,
    ProjectCostEntryORM.id,
)
Index(
    "idx_project_cost_entries_period",
    ProjectCostEntryORM.tenant_id,
    ProjectCostEntryORM.organization_id,
    ProjectCostEntryORM.financial_period_id,
)
Index(
    "idx_project_cost_entries_source",
    ProjectCostEntryORM.tenant_id,
    ProjectCostEntryORM.organization_id,
    ProjectCostEntryORM.source_module,
    ProjectCostEntryORM.source_type,
    ProjectCostEntryORM.source_id,
)
Index(
    "uq_project_cost_entries_one_reversal",
    ProjectCostEntryORM.tenant_id,
    ProjectCostEntryORM.organization_id,
    ProjectCostEntryORM.reverses_entry_id,
    unique=True,
    postgresql_where=ProjectCostEntryORM.reverses_entry_id.is_not(None),
    sqlite_where=ProjectCostEntryORM.reverses_entry_id.is_not(None),
)


__all__ = ["ProjectCostEntryORM"]
