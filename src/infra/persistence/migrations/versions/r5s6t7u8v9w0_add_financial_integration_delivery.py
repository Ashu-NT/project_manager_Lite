"""add owned financial integration outbox and inbox stores

Revision ID: r5s6t7u8v9w0
Revises: q4r5s6t7u8v9
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "r5s6t7u8v9w0"
down_revision = "q4r5s6t7u8v9"
branch_labels = None
depends_on = None

_TIME_OUTBOX = "platform_time_financial_outbox"
_PROCUREMENT_OUTBOX = "inventory_procurement_financial_outbox"
_PM_INBOX = "project_finance_inbox_receipts"


def _event_columns(*, include_published_at: bool) -> list[sa.Column]:
    columns = [
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=160), nullable=False),
        sa.Column("aggregate_type", sa.String(length=120), nullable=False),
        sa.Column("aggregate_id", sa.String(), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("envelope_json", sa.Text(), nullable=False),
        sa.Column("envelope_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_token", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=96), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    ]
    if include_published_at:
        columns.insert(17, sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    return columns


def upgrade() -> None:
    bind = op.get_bind()
    for table, prefix in ((_TIME_OUTBOX, "time_fin"), (_PROCUREMENT_OUTBOX, "proc_fin")):
        op.create_table(
            table,
            *_event_columns(include_published_at=True),
            sa.CheckConstraint(
                "status IN ('pending', 'claimed', 'retry', 'published', 'dead_letter')",
                name=f"ck_{prefix}_outbox_status",
            ),
            sa.CheckConstraint(
                "aggregate_version >= 1 AND version >= 1",
                name=f"ck_{prefix}_outbox_versions",
            ),
            sa.CheckConstraint(
                "attempt_count >= 0 AND max_attempts >= 1 AND attempt_count <= max_attempts",
                name=f"ck_{prefix}_outbox_attempts",
            ),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "organization_id", "event_id", name=f"uq_{prefix}_outbox_event"),
            info={"rls_scope": "tenant_organization"},
        )
        op.create_index(
            f"idx_{prefix}_outbox_claim", table,
            ["tenant_id", "organization_id", "status", "available_at", "occurred_at"],
        )

    op.create_table(
        _PM_INBOX,
        *_event_columns(include_published_at=False),
        sa.Column("consumer_name", sa.String(length=160), nullable=False),
        sa.Column("deduplication_key", sa.String(length=360), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quarantine_reason_code", sa.String(length=96), nullable=True),
        sa.Column("conflicting_envelope_json", sa.Text(), nullable=True),
        sa.Column("conflicting_envelope_hash", sa.String(length=64), nullable=True),
        sa.Column("conflict_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('processing', 'retry', 'processed', 'quarantined', 'dead_letter')",
            name="ck_pm_fin_inbox_status",
        ),
        sa.CheckConstraint("aggregate_version >= 1 AND version >= 1", name="ck_pm_fin_inbox_versions"),
        sa.CheckConstraint(
            "attempt_count >= 1 AND max_attempts >= 1 AND attempt_count <= max_attempts",
            name="ck_pm_fin_inbox_attempts",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "organization_id", "consumer_name", "event_id", name="uq_pm_fin_inbox_event"),
        sa.UniqueConstraint("tenant_id", "organization_id", "deduplication_key", name="uq_pm_fin_inbox_dedupe"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index("idx_pm_fin_inbox_claim", _PM_INBOX, ["tenant_id", "organization_id", "status", "available_at", "occurred_at"])
    op.create_index("idx_pm_fin_inbox_aggregate", _PM_INBOX, ["tenant_id", "organization_id", "consumer_name", "aggregate_type", "aggregate_id", "aggregate_version"])

    for table in (_TIME_OUTBOX, _PROCUREMENT_OUTBOX, _PM_INBOX):
        _create_envelope_guard(bind, table)
        enable_tenant_organization_rls(op, bind, table)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (_PM_INBOX, _PROCUREMENT_OUTBOX, _TIME_OUTBOX):
        disable_tenant_organization_rls(op, bind, table)
        _drop_envelope_guard(bind, table)
    op.drop_index("idx_pm_fin_inbox_aggregate", table_name=_PM_INBOX)
    op.drop_index("idx_pm_fin_inbox_claim", table_name=_PM_INBOX)
    op.drop_table(_PM_INBOX)
    op.drop_index("idx_proc_fin_outbox_claim", table_name=_PROCUREMENT_OUTBOX)
    op.drop_table(_PROCUREMENT_OUTBOX)
    op.drop_index("idx_time_fin_outbox_claim", table_name=_TIME_OUTBOX)
    op.drop_table(_TIME_OUTBOX)


_IMMUTABLE_COLUMNS = (
    "id", "tenant_id", "organization_id", "event_id", "event_type",
    "aggregate_type", "aggregate_id", "aggregate_version", "occurred_at",
    "envelope_json", "envelope_hash", "created_at",
)


def _create_envelope_guard(bind, table: str) -> None:
    if bind.dialect.name == "postgresql":
        function = f"protect_{table}_envelope"
        comparisons = " OR ".join(f"OLD.{column} IS DISTINCT FROM NEW.{column}" for column in _IMMUTABLE_COLUMNS)
        op.execute(f"CREATE FUNCTION {function}() RETURNS trigger AS $$ BEGIN IF {comparisons} THEN RAISE EXCEPTION '{table} envelope columns are immutable'; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql")
        op.execute(f"CREATE TRIGGER trg_{table}_envelope_immutable BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION {function}()")
    elif bind.dialect.name == "sqlite":
        comparison = " OR ".join(f"OLD.{column} IS NOT NEW.{column}" for column in _IMMUTABLE_COLUMNS)
        op.execute(f"CREATE TRIGGER trg_{table}_envelope_immutable BEFORE UPDATE ON {table} WHEN {comparison} BEGIN SELECT RAISE(ABORT, '{table} envelope columns are immutable'); END")


def _drop_envelope_guard(bind, table: str) -> None:
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_envelope_immutable")
    if bind.dialect.name == "postgresql":
        op.execute(f"DROP FUNCTION IF EXISTS protect_{table}_envelope()")
