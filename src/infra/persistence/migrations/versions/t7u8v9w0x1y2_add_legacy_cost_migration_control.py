"""add governed legacy CostItem migration controls

Revision ID: t7u8v9w0x1y2
Revises: s6t7u8v9w0x1
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.db.financial_numeric import FinancialNumericKind, financial_numeric
from src.infra.persistence.migrations.helpers.postgresql_rls import disable_tenant_organization_rls, enable_tenant_organization_rls


revision = "t7u8v9w0x1y2"
down_revision = "s6t7u8v9w0x1"
branch_labels = None
depends_on = None

_RUNS = "project_finance_legacy_migration_runs"
_ITEMS = "project_finance_legacy_migration_items"


def upgrade() -> None:
    op.create_table(
        _RUNS,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("fallback_transaction_date", sa.Date(), nullable=False),
        sa.Column("started_by", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_json", sa.Text(), server_default="{}", nullable=False),
        sa.CheckConstraint("mode IN ('dry_run', 'execute')", name="ck_pf_legacy_migration_runs_mode"),
        sa.CheckConstraint("status IN ('running', 'completed', 'completed_with_quarantine', 'failed')", name="ck_pf_legacy_migration_runs_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_legacy_migration_runs_scoped_project",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "organization_id", "id", name="uq_pf_legacy_migration_runs_scoped_id"),
        sa.UniqueConstraint("tenant_id", "organization_id", "project_id", "id", name="uq_pf_legacy_migration_runs_scoped_project_id"),
    )
    op.create_index("idx_pf_legacy_migration_runs_project", _RUNS, ["tenant_id", "organization_id", "project_id", "started_at"])

    op.create_table(
        _ITEMS,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("legacy_cost_item_id", sa.String(), nullable=False),
        sa.Column("purpose", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("last_run_id", sa.String(), nullable=False),
        sa.Column("source_amount", financial_numeric(FinancialNumericKind.MONEY), nullable=False),
        sa.Column("target_amount", financial_numeric(FinancialNumericKind.MONEY), nullable=False),
        sa.Column("rounding_delta", financial_numeric(FinancialNumericKind.MONEY), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("target_type", sa.String(length=64), server_default="", nullable=False),
        sa.Column("target_id", sa.String(), server_default="", nullable=False),
        sa.Column("reason_code", sa.String(length=96), server_default="", nullable=False),
        sa.Column("decision_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("purpose IN ('planned', 'commitment', 'actual', 'forecast')", name="ck_pf_legacy_migration_items_purpose"),
        sa.CheckConstraint("status IN ('eligible', 'migrated', 'quarantined', 'deferred', 'skipped')", name="ck_pf_legacy_migration_items_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_pf_legacy_migration_items_scoped_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "last_run_id"],
            [f"{_RUNS}.tenant_id", f"{_RUNS}.organization_id", f"{_RUNS}.project_id", f"{_RUNS}.id"],
            name="fk_pf_legacy_migration_items_scoped_run",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "organization_id", "legacy_cost_item_id", "purpose", name="uq_pf_legacy_migration_items_source_purpose"),
    )
    op.create_index("idx_pf_legacy_migration_items_project_status", _ITEMS, ["tenant_id", "organization_id", "project_id", "status"])

    bind = op.get_bind()
    enable_tenant_organization_rls(op, bind, _RUNS)
    enable_tenant_organization_rls(op, bind, _ITEMS)


def downgrade() -> None:
    bind = op.get_bind()
    disable_tenant_organization_rls(op, bind, _ITEMS)
    disable_tenant_organization_rls(op, bind, _RUNS)
    op.drop_index("idx_pf_legacy_migration_items_project_status", table_name=_ITEMS)
    op.drop_table(_ITEMS)
    op.drop_index("idx_pf_legacy_migration_runs_project", table_name=_RUNS)
    op.drop_table(_RUNS)
