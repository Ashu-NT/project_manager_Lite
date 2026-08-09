"""add canonical project commitments (Project Finance Phase C.3)

Revision ID: q4r5s6t7u8v9
Revises: p3q4r5s6t7u8
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "q4r5s6t7u8v9"
down_revision = "p3q4r5s6t7u8"
branch_labels = None
depends_on = None


_HEADERS = "project_commitments"
_LINES = "project_commitment_lines"
_REVISIONS = "project_commitment_source_revisions"
_MATCHES = "project_commitment_matches"


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        _HEADERS,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("purchase_order_id", sa.String(length=128), nullable=False),
        sa.Column("purchase_order_number", sa.String(length=128), nullable=False),
        sa.Column("supplier_party_id", sa.String(), nullable=False),
        sa.Column("site_id", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_project_commitments_scoped_project", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["supplier_party_id"], ["parties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_project_commitments_scoped_project_id",
        ),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "purchase_order_id",
            name="uq_project_commitments_source_po",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_project_commitments_scope_project", _HEADERS,
        ["tenant_id", "organization_id", "project_id"],
    )

    op.create_table(
        _LINES,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("commitment_id", sa.String(), nullable=False),
        sa.Column("purchase_order_line_id", sa.String(length=128), nullable=False),
        sa.Column("cost_code_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("ordered_quantity", sa.Numeric(19, 6), nullable=False),
        sa.Column("quantity_unit", sa.String(length=32), nullable=False),
        sa.Column("unit_price", sa.Numeric(19, 8), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("base_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("base_currency_code", sa.String(length=8), nullable=False),
        sa.Column("exchange_rate", sa.Numeric(24, 12), nullable=False),
        sa.Column("exchange_rate_date", sa.Date(), nullable=False),
        sa.Column("exchange_rate_source", sa.String(length=128), nullable=False),
        sa.Column("exchange_rate_captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("matched_amount", sa.Numeric(19, 4), nullable=False, server_default="0"),
        sa.Column("order_date", sa.Date(), nullable=True),
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
        sa.Column("source_requisition_id", sa.String(length=128), nullable=True),
        sa.Column("source_requisition_line_id", sa.String(length=128), nullable=True),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("source_content_hash", sa.String(length=64), nullable=False),
        sa.Column("source_idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('sent', 'partially_received', 'fully_received', 'closed', 'cancelled')",
            name="ck_project_commitment_lines_state",
        ),
        sa.CheckConstraint("ordered_quantity > 0", name="ck_project_commitment_lines_quantity"),
        sa.CheckConstraint("unit_price >= 0", name="ck_project_commitment_lines_rate"),
        sa.CheckConstraint(
            "amount >= 0 AND base_amount >= 0 AND matched_amount >= 0 "
            "AND matched_amount <= amount", name="ck_project_commitment_lines_amounts",
        ),
        sa.CheckConstraint("exchange_rate > 0", name="ck_project_commitment_lines_fx"),
        sa.CheckConstraint(
            "source_revision >= 1 AND version >= 1",
            name="ck_project_commitment_lines_versions",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name="fk_project_commitment_lines_scoped_project", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "commitment_id"],
            [
                "project_commitments.tenant_id", "project_commitments.organization_id",
                "project_commitments.project_id", "project_commitments.id",
            ],
            name="fk_project_commitment_lines_scoped_header", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "cost_code_id"],
            [
                "project_finance_cost_codes.tenant_id",
                "project_finance_cost_codes.organization_id",
                "project_finance_cost_codes.id",
            ],
            name="fk_project_commitment_lines_scoped_cost_code", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "task_id"], ["tasks.project_id", "tasks.id"],
            name="fk_project_commitment_lines_project_task", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_project_commitment_lines_scoped_project_id",
        ),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "commitment_id", "purchase_order_line_id",
            name="uq_project_commitment_lines_source_line",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_project_commitment_lines_project_state", _LINES,
        ["tenant_id", "organization_id", "project_id", "state"],
    )

    op.create_table(
        _REVISIONS,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("commitment_line_id", sa.String(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("source_content_hash", sa.String(length=64), nullable=False),
        sa.Column("source_idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source_revision >= 1", name="ck_project_commitment_revisions_version"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "commitment_line_id"],
            [
                "project_commitment_lines.tenant_id", "project_commitment_lines.organization_id",
                "project_commitment_lines.project_id", "project_commitment_lines.id",
            ],
            name="fk_project_commitment_revisions_scoped_line", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "commitment_line_id", "source_revision",
            name="uq_project_commitment_revisions_line_revision",
        ),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "source_idempotency_key",
            name="uq_project_commitment_revisions_idempotency",
        ),
        info={"rls_scope": "tenant_organization"},
    )

    op.create_table(
        _MATCHES,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("commitment_line_id", sa.String(), nullable=False),
        sa.Column("cost_entry_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("reverses_match_id", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('match', 'reversal')", name="ck_project_commitment_matches_kind"),
        sa.CheckConstraint(
            "(kind = 'match' AND amount > 0 AND reverses_match_id IS NULL) OR "
            "(kind = 'reversal' AND amount < 0 AND reverses_match_id IS NOT NULL)",
            name="ck_project_commitment_matches_sign",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "commitment_line_id"],
            [
                "project_commitment_lines.tenant_id", "project_commitment_lines.organization_id",
                "project_commitment_lines.project_id", "project_commitment_lines.id",
            ],
            name="fk_project_commitment_matches_scoped_line", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "cost_entry_id"],
            [
                "project_cost_entries.tenant_id", "project_cost_entries.organization_id",
                "project_cost_entries.project_id", "project_cost_entries.id",
            ],
            name="fk_project_commitment_matches_scoped_cost_entry", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "reverses_match_id"],
            [
                "project_commitment_matches.tenant_id", "project_commitment_matches.organization_id",
                "project_commitment_matches.project_id", "project_commitment_matches.id",
            ],
            name="fk_project_commitment_matches_scoped_reversal", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "project_id", "id",
            name="uq_project_commitment_matches_scoped_project_id",
        ),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "idempotency_key",
            name="uq_project_commitment_matches_idempotency",
        ),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index(
        "idx_project_commitment_matches_line", _MATCHES,
        ["tenant_id", "organization_id", "commitment_line_id", "created_at"],
    )
    op.create_index(
        "uq_project_commitment_matches_original_actual", _MATCHES,
        ["tenant_id", "organization_id", "cost_entry_id"], unique=True,
        postgresql_where=sa.text("kind = 'match'"), sqlite_where=sa.text("kind = 'match'"),
    )
    op.create_index(
        "uq_project_commitment_matches_one_reversal", _MATCHES,
        ["tenant_id", "organization_id", "reverses_match_id"], unique=True,
        postgresql_where=sa.text("reverses_match_id IS NOT NULL"),
        sqlite_where=sa.text("reverses_match_id IS NOT NULL"),
    )

    _create_immutable_ledger_guards(bind)
    for table in (_HEADERS, _LINES, _REVISIONS, _MATCHES):
        enable_tenant_organization_rls(op, bind, table)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (_MATCHES, _REVISIONS, _LINES, _HEADERS):
        disable_tenant_organization_rls(op, bind, table)
    _drop_immutable_ledger_guards(bind)
    op.drop_index("uq_project_commitment_matches_one_reversal", table_name=_MATCHES)
    op.drop_index("uq_project_commitment_matches_original_actual", table_name=_MATCHES)
    op.drop_index("idx_project_commitment_matches_line", table_name=_MATCHES)
    op.drop_table(_MATCHES)
    op.drop_table(_REVISIONS)
    op.drop_index("idx_project_commitment_lines_project_state", table_name=_LINES)
    op.drop_table(_LINES)
    op.drop_index("idx_project_commitments_scope_project", table_name=_HEADERS)
    op.drop_table(_HEADERS)


def _create_immutable_ledger_guards(bind) -> None:
    for table in (_REVISIONS, _MATCHES):
        if bind.dialect.name == "postgresql":
            function = f"prevent_{table}_mutation"
            op.execute(
                f"""
                CREATE FUNCTION {function}() RETURNS trigger AS $$
                BEGIN
                    RAISE EXCEPTION '{table} rows are immutable';
                END;
                $$ LANGUAGE plpgsql
                """
            )
            op.execute(
                f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION {function}()"
            )
        elif bind.dialect.name == "sqlite":
            for operation in ("UPDATE", "DELETE"):
                suffix = operation.lower()
                op.execute(
                    f"CREATE TRIGGER trg_{table}_immutable_{suffix} BEFORE {operation} ON {table} "
                    f"BEGIN SELECT RAISE(ABORT, '{table} rows are immutable'); END"
                )


def _drop_immutable_ledger_guards(bind) -> None:
    for table in (_MATCHES, _REVISIONS):
        if bind.dialect.name == "postgresql":
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
            op.execute(f"DROP FUNCTION IF EXISTS prevent_{table}_mutation()")
        elif bind.dialect.name == "sqlite":
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable_update")
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable_delete")
