"""add canonical project cost entries (Project Finance Phase C.2)

Revision ID: p3q4r5s6t7u8
Revises: o2p3q4r5s6t7
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "p3q4r5s6t7u8"
down_revision = "o2p3q4r5s6t7"
branch_labels = None
depends_on = None


_TABLE = "project_cost_entries"
_IMMUTABLE_COLUMNS = (
    "tenant_id",
    "organization_id",
    "project_id",
    "description",
    "entry_kind",
    "amount",
    "currency_code",
    "base_amount",
    "base_currency_code",
    "exchange_rate",
    "exchange_rate_date",
    "exchange_rate_source",
    "exchange_rate_captured_at",
    "transaction_date",
    "posting_date",
    "financial_period_id",
    "cost_code_id",
    "task_id",
    "resource_id",
    "source_module",
    "source_type",
    "source_id",
    "source_line_id",
    "source_revision",
    "source_content_hash",
    "posting_purpose",
    "idempotency_key",
    "reverses_entry_id",
    "created_by",
    "created_at",
    "submitted_by",
    "submitted_at",
    "approved_by",
    "approved_at",
    "posted_by",
    "posted_at",
)


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("entry_kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("base_amount", sa.Numeric(19, 4), nullable=True),
        sa.Column("base_currency_code", sa.String(length=8), nullable=True),
        sa.Column("exchange_rate", sa.Numeric(24, 12), nullable=True),
        sa.Column("exchange_rate_date", sa.Date(), nullable=True),
        sa.Column("exchange_rate_source", sa.String(length=128), nullable=True),
        sa.Column("exchange_rate_captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("posting_date", sa.Date(), nullable=True),
        sa.Column("financial_period_id", sa.String(), nullable=True),
        sa.Column("cost_code_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("source_module", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("source_line_id", sa.String(length=128), nullable=True),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("source_content_hash", sa.String(length=64), nullable=False),
        sa.Column("posting_purpose", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("reverses_entry_id", sa.String(), nullable=True),
        sa.Column("reversed_by_entry_id", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_by", sa.String(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_notes", sa.String(), nullable=False, server_default=""),
        sa.Column("posted_by", sa.String(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by", sa.String(), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "entry_kind IN ('actual', 'adjustment', 'reversal')",
            name="ck_project_cost_entries_kind",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'posted', 'reversed')",
            name="ck_project_cost_entries_status",
        ),
        sa.CheckConstraint(
            "(entry_kind = 'actual' AND amount > 0 AND reverses_entry_id IS NULL) OR "
            "(entry_kind = 'adjustment' AND amount <> 0 AND reverses_entry_id IS NULL) OR "
            "(entry_kind = 'reversal' AND amount < 0 AND reverses_entry_id IS NOT NULL)",
            name="ck_project_cost_entries_sign_and_reversal",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            "exchange_rate IS NULL OR exchange_rate > 0",
            name="ck_project_cost_entries_exchange_rate",
        ),
        sa.CheckConstraint(
            "base_amount IS NULL OR (base_amount <> 0 AND amount * base_amount > 0)",
            name="ck_project_cost_entries_base_sign",
        ),
        sa.CheckConstraint("version >= 1", name="ck_project_cost_entries_version"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_project_cost_entries_tenant", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_project_cost_entries_scoped_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_project_cost_entries_scoped_cost_code",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "task_id"],
            ["tasks.project_id", "tasks.id"],
            name="fk_project_cost_entries_project_task",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"], ["resources.id"], name="fk_project_cost_entries_resource", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "financial_period_id"],
            ["financial_periods.tenant_id", "financial_periods.organization_id", "financial_periods.id"],
            name="fk_project_cost_entries_scoped_period",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_project_cost_entries_scoped_project_id",
        ),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "idempotency_key",
            name="uq_project_cost_entries_idempotency",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_project_cost_entries_scope_project",
        _TABLE,
        ["tenant_id", "organization_id", "project_id"],
    )
    op.create_index(
        "idx_project_cost_entries_project_posting",
        _TABLE,
        ["project_id", "posting_date", "id"],
    )
    op.create_index(
        "idx_project_cost_entries_period",
        _TABLE,
        ["tenant_id", "organization_id", "financial_period_id"],
    )
    op.create_index(
        "idx_project_cost_entries_source",
        _TABLE,
        ["tenant_id", "organization_id", "source_module", "source_type", "source_id"],
    )
    op.create_index(
        "uq_project_cost_entries_one_reversal",
        _TABLE,
        ["tenant_id", "organization_id", "reverses_entry_id"],
        unique=True,
        postgresql_where=sa.text("reverses_entry_id IS NOT NULL"),
        sqlite_where=sa.text("reverses_entry_id IS NOT NULL"),
    )
    _create_immutability_guards(bind)
    enable_tenant_organization_rls(op, bind, _TABLE)


def downgrade() -> None:
    bind = op.get_bind()
    disable_tenant_organization_rls(op, bind, _TABLE)
    _drop_immutability_guards(bind)
    op.drop_index("uq_project_cost_entries_one_reversal", table_name=_TABLE)
    op.drop_index("idx_project_cost_entries_source", table_name=_TABLE)
    op.drop_index("idx_project_cost_entries_period", table_name=_TABLE)
    op.drop_index("idx_project_cost_entries_project_posting", table_name=_TABLE)
    op.drop_index("idx_project_cost_entries_scope_project", table_name=_TABLE)
    op.drop_table(_TABLE)


def _create_immutability_guards(bind) -> None:
    if bind.dialect.name == "postgresql":
        comparisons = " OR ".join(
            f"OLD.{column} IS DISTINCT FROM NEW.{column}" for column in _IMMUTABLE_COLUMNS
        )
        op.execute(
            f"""
            CREATE FUNCTION prevent_project_cost_entry_mutation() RETURNS trigger AS $$
            BEGIN
                IF OLD.status IN ('posted', 'reversed') AND (
                    ({comparisons})
                    OR (OLD.status = 'reversed' AND NEW.status <> 'reversed')
                    OR (OLD.status = 'posted' AND NEW.status NOT IN ('posted', 'reversed'))
                ) THEN
                    RAISE EXCEPTION 'posted project cost entry financial facts are immutable';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER trg_project_cost_entries_immutable_update
            BEFORE UPDATE ON {_TABLE}
            FOR EACH ROW EXECUTE FUNCTION prevent_project_cost_entry_mutation()
            """
        )
        op.execute(
            f"""
            CREATE FUNCTION prevent_project_cost_entry_delete() RETURNS trigger AS $$
            BEGIN
                IF OLD.status IN ('posted', 'reversed') THEN
                    RAISE EXCEPTION 'posted project cost entries cannot be deleted';
                END IF;
                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER trg_project_cost_entries_immutable_delete
            BEFORE DELETE ON {_TABLE}
            FOR EACH ROW EXECUTE FUNCTION prevent_project_cost_entry_delete()
            """
        )
    elif bind.dialect.name == "sqlite":
        comparisons = " OR ".join(
            f"OLD.{column} IS NOT NEW.{column}" for column in _IMMUTABLE_COLUMNS
        )
        op.execute(
            f"""
            CREATE TRIGGER trg_project_cost_entries_immutable_update
            BEFORE UPDATE ON {_TABLE}
            WHEN OLD.status IN ('posted', 'reversed') AND (
                ({comparisons})
                OR (OLD.status = 'reversed' AND NEW.status <> 'reversed')
                OR (OLD.status = 'posted' AND NEW.status NOT IN ('posted', 'reversed'))
            )
            BEGIN
                SELECT RAISE(ABORT, 'posted project cost entry financial facts are immutable');
            END
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER trg_project_cost_entries_immutable_delete
            BEFORE DELETE ON {_TABLE}
            WHEN OLD.status IN ('posted', 'reversed')
            BEGIN
                SELECT RAISE(ABORT, 'posted project cost entries cannot be deleted');
            END
            """
        )


def _drop_immutability_guards(bind) -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_project_cost_entries_immutable_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_project_cost_entries_immutable_update")
    if bind.dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS prevent_project_cost_entry_delete()")
        op.execute("DROP FUNCTION IF EXISTS prevent_project_cost_entry_mutation()")
