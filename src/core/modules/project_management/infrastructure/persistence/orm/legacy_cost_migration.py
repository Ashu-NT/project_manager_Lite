from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.db.financial_numeric import FinancialNumericKind, financial_numeric, financial_numeric_info
from src.infra.persistence.orm.base import Base


class LegacyCostMigrationRunORM(Base):
    __tablename__ = "project_finance_legacy_migration_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_legacy_migration_runs_scoped_project",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "id",
            name="uq_pf_legacy_migration_runs_scoped_id",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_pf_legacy_migration_runs_scoped_project_id",
        ),
        CheckConstraint("mode IN ('dry_run', 'execute')", name="ck_pf_legacy_migration_runs_mode"),
        CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_quarantine', 'failed')",
            name="ck_pf_legacy_migration_runs_status",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    fallback_transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    started_by: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")


class LegacyCostMigrationItemORM(Base):
    __tablename__ = "project_finance_legacy_migration_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_legacy_migration_items_scoped_project",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "last_run_id"],
            [
                "project_finance_legacy_migration_runs.tenant_id",
                "project_finance_legacy_migration_runs.organization_id",
                "project_finance_legacy_migration_runs.project_id",
                "project_finance_legacy_migration_runs.id",
            ],
            name="fk_pf_legacy_migration_items_scoped_run",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id", "organization_id", "legacy_cost_item_id", "purpose",
            name="uq_pf_legacy_migration_items_source_purpose",
        ),
        CheckConstraint("purpose IN ('planned', 'commitment', 'actual', 'forecast')", name="ck_pf_legacy_migration_items_purpose"),
        CheckConstraint(
            "status IN ('eligible', 'migrated', 'quarantined', 'deferred', 'skipped')",
            name="ck_pf_legacy_migration_items_status",
        ),
        {"info": {"rls_scope": "tenant_organization"}},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str] = mapped_column(String, nullable=False)
    legacy_cost_item_id: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    last_run_id: Mapped[str] = mapped_column(String, nullable=False)
    source_amount: Mapped[Decimal] = mapped_column(financial_numeric(FinancialNumericKind.MONEY), nullable=False, info=financial_numeric_info(FinancialNumericKind.MONEY))
    target_amount: Mapped[Decimal] = mapped_column(financial_numeric(FinancialNumericKind.MONEY), nullable=False, info=financial_numeric_info(FinancialNumericKind.MONEY))
    rounding_delta: Mapped[Decimal] = mapped_column(financial_numeric(FinancialNumericKind.MONEY), nullable=False, info=financial_numeric_info(FinancialNumericKind.MONEY))
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    target_id: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    reason_code: Mapped[str] = mapped_column(String(96), nullable=False, default="", server_default="")
    decision_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("idx_pf_legacy_migration_runs_project", LegacyCostMigrationRunORM.tenant_id, LegacyCostMigrationRunORM.organization_id, LegacyCostMigrationRunORM.project_id, LegacyCostMigrationRunORM.started_at)
Index("idx_pf_legacy_migration_items_project_status", LegacyCostMigrationItemORM.tenant_id, LegacyCostMigrationItemORM.organization_id, LegacyCostMigrationItemORM.project_id, LegacyCostMigrationItemORM.status)


__all__ = ["LegacyCostMigrationItemORM", "LegacyCostMigrationRunORM"]
