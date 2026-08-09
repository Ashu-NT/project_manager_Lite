"""add immutable approved Time labor posting snapshots

Revision ID: s6t7u8v9w0x1
Revises: r5s6t7u8v9w0
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.db.financial_numeric import FinancialNumericKind, financial_numeric
from src.infra.persistence.migrations.helpers.postgresql_rls import disable_tenant_organization_rls, enable_tenant_organization_rls


revision = "s6t7u8v9w0x1"
down_revision = "r5s6t7u8v9w0"
branch_labels = None
depends_on = None

_TABLE = "project_approved_time_labor_postings"


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("time_entry_id", sa.String(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("source_content_hash", sa.String(length=64), nullable=False),
        sa.Column("approved_snapshot_id", sa.String(), nullable=False),
        sa.Column("timesheet_period_id", sa.String(), nullable=False),
        sa.Column("actual_cost_entry_id", sa.String(), nullable=False),
        sa.Column("reversal_cost_entry_id", sa.String(), nullable=True),
        sa.Column("hours", financial_numeric(FinancialNumericKind.QUANTITY), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("rate_amount", financial_numeric(FinancialNumericKind.RATE), nullable=False),
        sa.Column("rate_currency", sa.String(length=8), nullable=False),
        sa.Column("rate_card_id", sa.String(), nullable=False),
        sa.Column("rate_line_id", sa.String(), nullable=False),
        sa.Column("rate_card_version", sa.Integer(), nullable=False),
        sa.Column("rate_precedence_level", sa.Integer(), nullable=False),
        sa.Column("rate_effective_date", sa.Date(), nullable=False),
        sa.Column("rate_resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("employee_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source_revision >= 1 AND hours > 0 AND rate_amount >= 0", name="ck_labor_postings_values"),
        sa.CheckConstraint("rate_card_version >= 1 AND rate_precedence_level >= 1", name="ck_labor_postings_rate_versions"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "organization_id", "project_id"], ["projects.tenant_id", "projects.organization_id", "projects.id"], name="fk_labor_postings_scoped_project", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id", "organization_id", "project_id", "actual_cost_entry_id"], ["project_cost_entries.tenant_id", "project_cost_entries.organization_id", "project_cost_entries.project_id", "project_cost_entries.id"], name="fk_labor_postings_scoped_actual", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "organization_id", "project_id", "reversal_cost_entry_id"], ["project_cost_entries.tenant_id", "project_cost_entries.organization_id", "project_cost_entries.project_id", "project_cost_entries.id"], name="fk_labor_postings_scoped_reversal", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "organization_id", "time_entry_id", "source_revision", name="uq_labor_postings_source_revision"),
        sa.UniqueConstraint("tenant_id", "organization_id", "approved_snapshot_id", name="uq_labor_postings_snapshot"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index("idx_labor_postings_latest", _TABLE, ["tenant_id", "organization_id", "time_entry_id", "source_revision"])
    _create_immutable_guard(bind)
    enable_tenant_organization_rls(op, bind, _TABLE)


def downgrade() -> None:
    bind = op.get_bind()
    disable_tenant_organization_rls(op, bind, _TABLE)
    _drop_immutable_guard(bind)
    op.drop_index("idx_labor_postings_latest", table_name=_TABLE)
    op.drop_table(_TABLE)


def _create_immutable_guard(bind) -> None:
    if bind.dialect.name == "postgresql":
        op.execute(f"CREATE FUNCTION prevent_{_TABLE}_mutation() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION '{_TABLE} rows are immutable'; END; $$ LANGUAGE plpgsql")
        op.execute(f"CREATE TRIGGER trg_{_TABLE}_immutable BEFORE UPDATE OR DELETE ON {_TABLE} FOR EACH ROW EXECUTE FUNCTION prevent_{_TABLE}_mutation()")
    elif bind.dialect.name == "sqlite":
        for operation in ("UPDATE", "DELETE"):
            op.execute(f"CREATE TRIGGER trg_{_TABLE}_immutable_{operation.lower()} BEFORE {operation} ON {_TABLE} BEGIN SELECT RAISE(ABORT, '{_TABLE} rows are immutable'); END")


def _drop_immutable_guard(bind) -> None:
    if bind.dialect.name == "postgresql":
        op.execute(f"DROP TRIGGER IF EXISTS trg_{_TABLE}_immutable ON {_TABLE}")
        op.execute(f"DROP FUNCTION IF EXISTS prevent_{_TABLE}_mutation()")
    elif bind.dialect.name == "sqlite":
        op.execute(f"DROP TRIGGER IF EXISTS trg_{_TABLE}_immutable_update")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{_TABLE}_immutable_delete")
