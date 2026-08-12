"""Add PM billing preparation and external accounting evidence.

Revision ID: pfbill_e1_001
Revises: pfnum_d8_002
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.infra.persistence.migrations.helpers.postgresql_rls import (
    disable_tenant_organization_rls,
    enable_tenant_organization_rls,
)


revision = "pfbill_e1_001"
down_revision = "pfnum_d8_002"
branch_labels = None
depends_on = None

_MONEY = sa.Numeric(19, 4, asdecimal=True)
_RATE = sa.Numeric(19, 6, asdecimal=True)
_QUANTITY = sa.Numeric(19, 6, asdecimal=True)
_PERCENTAGE = sa.Numeric(9, 6, asdecimal=True)
_TABLES = (
    "project_billing_profiles",
    "project_billing_schedule_lines",
    "project_billing_preparations",
    "project_billing_preparation_lines",
    "project_billing_source_locks",
    "project_billing_external_events",
)


def _scope_columns() -> tuple[sa.Column, sa.Column, sa.Column]:
    return (
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
    )


def _scope_constraints(prefix: str, *, project_delete: str = "CASCADE") -> tuple:
    return (
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            name=f"fk_{prefix}_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id"],
            ["organizations.tenant_id", "organizations.id"],
            name=f"fk_{prefix}_scoped_organization", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id"],
            ["projects.tenant_id", "projects.organization_id", "projects.id"],
            name=f"fk_{prefix}_scoped_project", ondelete=project_delete,
        ),
    )


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "project_billing_profiles",
        sa.Column("id", sa.String(), nullable=False),
        *_scope_columns(),
        sa.Column("currency_code", sa.String(8), nullable=False),
        sa.Column("contract_reference", sa.String(128), nullable=False),
        sa.Column("contract_value", _MONEY, nullable=False),
        sa.Column("customer_party_id", sa.String(), nullable=True),
        sa.Column("external_customer_reference", sa.String(128), nullable=True),
        sa.Column("purchase_order_reference", sa.String(128), nullable=True),
        sa.Column("cost_plus_markup_percent", _PERCENTAGE, nullable=False, server_default="0"),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("retention_years", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *_scope_constraints("billing_profiles"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "organization_id", "project_id", name="uq_billing_profiles_project"),
        sa.UniqueConstraint("tenant_id", "organization_id", "project_id", "id", name="uq_billing_profiles_scoped_id"),
        sa.CheckConstraint("status IN ('draft', 'active', 'on_hold', 'closed')", name="ck_billing_profiles_status"),
        sa.CheckConstraint("contract_value >= 0", name="ck_billing_profiles_contract_value"),
        sa.CheckConstraint("cost_plus_markup_percent >= 0 AND cost_plus_markup_percent <= 1000", name="ck_billing_profiles_markup"),
        sa.CheckConstraint("payment_terms_days >= 0 AND payment_terms_days <= 3650", name="ck_billing_profiles_payment_terms"),
        sa.CheckConstraint("retention_years >= 7 AND retention_years <= 100", name="ck_billing_profiles_retention"),
        sa.CheckConstraint("version >= 1", name="ck_billing_profiles_version"),
        sa.CheckConstraint("external_customer_reference IS NULL OR customer_party_id IS NOT NULL", name="ck_billing_profiles_external_customer_party"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index("idx_billing_profiles_scope", "project_billing_profiles", ["tenant_id", "organization_id"])

    op.create_table(
        "project_billing_schedule_lines",
        sa.Column("id", sa.String(), nullable=False),
        *_scope_columns(),
        sa.Column("billing_profile_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("amount", _MONEY, nullable=False),
        sa.Column("currency_code", sa.String(8), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("acceptance_reference", sa.String(200), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="planned"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *_scope_constraints("billing_schedule"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "billing_profile_id"],
            ["project_billing_profiles.tenant_id", "project_billing_profiles.organization_id", "project_billing_profiles.project_id", "project_billing_profiles.id"],
            name="fk_billing_schedule_scoped_profile", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name="fk_billing_schedule_task", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount > 0", name="ck_billing_schedule_amount"),
        sa.CheckConstraint("status IN ('planned', 'ready', 'billed', 'cancelled')", name="ck_billing_schedule_status"),
        sa.CheckConstraint("version >= 1", name="ck_billing_schedule_version"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index("idx_billing_schedule_project", "project_billing_schedule_lines", ["tenant_id", "organization_id", "project_id"])
    op.create_index("idx_billing_schedule_due", "project_billing_schedule_lines", ["due_date"])

    op.create_table(
        "project_billing_preparations",
        sa.Column("id", sa.String(), nullable=False),
        *_scope_columns(),
        sa.Column("billing_profile_id", sa.String(), nullable=False),
        sa.Column("preparation_number", sa.String(64), nullable=False),
        sa.Column("billing_method", sa.String(32), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("currency_code", sa.String(8), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("line_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_amount", _MONEY, nullable=False, server_default="0"),
        sa.Column("correction_of_preparation_id", sa.String(), nullable=True),
        sa.Column("approval_request_id", sa.String(), nullable=True),
        sa.Column("submitted_by", sa.String(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_notes", sa.String(), nullable=False, server_default=""),
        sa.Column("delivery_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *_scope_constraints("billing_preparations", project_delete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "billing_profile_id"],
            ["project_billing_profiles.tenant_id", "project_billing_profiles.organization_id", "project_billing_profiles.project_id", "project_billing_profiles.id"],
            name="fk_billing_preparations_scoped_profile", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "correction_of_preparation_id"],
            ["project_billing_preparations.tenant_id", "project_billing_preparations.organization_id", "project_billing_preparations.project_id", "project_billing_preparations.id"],
            name="fk_billing_preparations_scoped_correction", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "organization_id", "preparation_number", name="uq_billing_preparations_number"),
        sa.UniqueConstraint("tenant_id", "organization_id", "idempotency_key", name="uq_billing_preparations_idempotency"),
        sa.UniqueConstraint("tenant_id", "organization_id", "project_id", "id", name="uq_billing_preparations_scoped_id"),
        sa.CheckConstraint("billing_method IN ('time_and_materials', 'fixed_price', 'cost_plus')", name="ck_billing_preparations_method"),
        sa.CheckConstraint("period_end >= period_start", name="ck_billing_preparations_period"),
        sa.CheckConstraint("line_count >= 0", name="ck_billing_preparations_line_count"),
        sa.CheckConstraint("total_amount >= 0 OR correction_of_preparation_id IS NOT NULL", name="ck_billing_preparations_negative_correction"),
        sa.CheckConstraint("status IN ('draft', 'submitted', 'approved', 'delivery_pending', 'delivered', 'acknowledged', 'reconciled', 'rejected', 'cancelled')", name="ck_billing_preparations_status"),
        sa.CheckConstraint("version >= 1", name="ck_billing_preparations_version"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index("idx_billing_preparations_project", "project_billing_preparations", ["tenant_id", "organization_id", "project_id"])
    op.create_index("idx_billing_preparations_status", "project_billing_preparations", ["status"])

    op.create_table(
        "project_billing_preparation_lines",
        sa.Column("id", sa.String(), nullable=False),
        *_scope_columns(),
        sa.Column("preparation_id", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(24), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("source_revision", sa.String(64), nullable=False),
        sa.Column("source_content_hash", sa.String(64), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("source_date", sa.Date(), nullable=False),
        sa.Column("quantity", _QUANTITY, nullable=False),
        sa.Column("unit", sa.String(24), nullable=False),
        sa.Column("unit_rate", _RATE, nullable=False),
        sa.Column("net_amount", _MONEY, nullable=False),
        sa.Column("currency_code", sa.String(8), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("source_amount", _MONEY, nullable=True),
        sa.Column("markup_percent", _PERCENTAGE, nullable=True),
        sa.Column("rate_card_id", sa.String(), nullable=True),
        sa.Column("rate_line_id", sa.String(), nullable=True),
        sa.Column("rate_card_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        *_scope_constraints("billing_lines", project_delete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "preparation_id"],
            ["project_billing_preparations.tenant_id", "project_billing_preparations.organization_id", "project_billing_preparations.project_id", "project_billing_preparations.id"],
            name="fk_billing_lines_scoped_preparation", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("source_type IN ('approved_time', 'posted_cost', 'schedule_line', 'adjustment')", name="ck_billing_lines_source_type"),
        sa.CheckConstraint("quantity <> 0", name="ck_billing_lines_quantity"),
        sa.CheckConstraint("net_amount <> 0", name="ck_billing_lines_net_amount"),
        sa.CheckConstraint("(rate_card_id IS NULL AND rate_line_id IS NULL AND rate_card_version IS NULL) OR (rate_card_id IS NOT NULL AND rate_line_id IS NOT NULL AND rate_card_version >= 1)", name="ck_billing_lines_rate_snapshot"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index("idx_billing_lines_preparation", "project_billing_preparation_lines", ["preparation_id"])
    op.create_index("idx_billing_lines_source", "project_billing_preparation_lines", ["tenant_id", "organization_id", "source_type", "source_id"])

    op.create_table(
        "project_billing_source_locks",
        sa.Column("id", sa.String(), nullable=False),
        *_scope_columns(),
        sa.Column("source_type", sa.String(24), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("source_revision", sa.String(64), nullable=False),
        sa.Column("source_content_hash", sa.String(64), nullable=False),
        sa.Column("preparation_id", sa.String(), nullable=False),
        sa.Column("preparation_line_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="reserved"),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        *_scope_constraints("billing_locks", project_delete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "preparation_id"],
            ["project_billing_preparations.tenant_id", "project_billing_preparations.organization_id", "project_billing_preparations.project_id", "project_billing_preparations.id"],
            name="fk_billing_locks_scoped_preparation", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["preparation_line_id"], ["project_billing_preparation_lines.id"], name="fk_billing_locks_line", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "organization_id", "source_type", "source_id", name="uq_billing_locks_source"),
        sa.CheckConstraint("status IN ('reserved', 'finalized', 'released')", name="ck_billing_locks_status"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index("idx_billing_locks_preparation", "project_billing_source_locks", ["tenant_id", "organization_id", "preparation_id"])

    op.create_table(
        "project_billing_external_events",
        sa.Column("id", sa.String(), nullable=False),
        *_scope_columns(),
        sa.Column("preparation_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("external_system", sa.String(80), nullable=False),
        sa.Column("external_status", sa.String(80), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_invoice_reference", sa.String(160), nullable=True),
        sa.Column("reconciliation_reference", sa.String(160), nullable=True),
        sa.Column("message", sa.String(500), nullable=False, server_default=""),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        *_scope_constraints("billing_events", project_delete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_id", "project_id", "preparation_id"],
            ["project_billing_preparations.tenant_id", "project_billing_preparations.organization_id", "project_billing_preparations.project_id", "project_billing_preparations.id"],
            name="fk_billing_events_scoped_preparation", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "organization_id", "external_system", "idempotency_key", name="uq_billing_events_idempotency"),
        sa.CheckConstraint("event_type IN ('delivery_accepted', 'delivery_rejected', 'status_updated', 'reconciled')", name="ck_billing_events_type"),
        sa.CheckConstraint("event_type <> 'reconciled' OR reconciliation_reference IS NOT NULL", name="ck_billing_events_reconciliation"),
        info={"rls_scope": "tenant_organization"},
    )
    op.create_index("idx_billing_events_preparation", "project_billing_external_events", ["tenant_id", "organization_id", "preparation_id", "occurred_at"])

    for table_name in _TABLES:
        enable_tenant_organization_rls(op, bind, table_name)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(_TABLES):
        disable_tenant_organization_rls(op, bind, table_name)
        op.drop_table(table_name)
