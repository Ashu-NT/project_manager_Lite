"""Optional Accounting connector and atomic PM handoff outbox.

Revision ID: a7c4e1b9d625
Revises: d6a3f8c2b951
"""
from alembic import op
import sqlalchemy as sa

from src.infra.persistence.migrations.helpers.postgresql_rls import enable_tenant_organization_rls

revision = "a7c4e1b9d625"
down_revision = "d6a3f8c2b951"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organization_accounting_connectors",
        sa.Column("tenant_id", sa.String(), primary_key=True),
        sa.Column("organization_id", sa.String(), primary_key=True),
        sa.Column("adapter_id", sa.String(128), nullable=False),
        sa.Column("connection_id", sa.String(128), nullable=False),
        sa.Column("secret_reference", sa.String(128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "organization_id"], ["organizations.tenant_id", "organizations.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("version >= 1", name="ck_accounting_connector_version"),
    )
    op.create_table(
        "project_accounting_handoffs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("preparation_id", sa.String(), nullable=False),
        sa.Column("approved_version", sa.Integer(), nullable=False),
        sa.Column("handoff_kind", sa.String(), nullable=False),
        sa.Column("payload_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "organization_id", "project_id", "preparation_id"], ["project_billing_preparations.tenant_id", "project_billing_preparations.organization_id", "project_billing_preparations.project_id", "project_billing_preparations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "organization_id", "project_id", "preparation_id", "approved_version", "handoff_kind", name="uq_pm_accounting_handoff_business"),
        sa.UniqueConstraint("tenant_id", "organization_id", "project_id", "id", name="uq_pm_accounting_handoff_scope"),
        sa.CheckConstraint("approved_version >= 1", name="ck_pm_accounting_approved_version"),
        sa.CheckConstraint("handoff_kind = 'billing_preparation'", name="ck_pm_accounting_handoff_kind"),
    )
    op.create_table(
        "project_accounting_outbox",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(160), nullable=False),
        sa.Column("aggregate_type", sa.String(120), nullable=False),
        sa.Column("aggregate_id", sa.String(), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("envelope_json", sa.Text(), nullable=False),
        sa.Column("envelope_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_token", sa.String(128)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_code", sa.String(96)),
        sa.Column("last_error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["tenant_id", "organization_id", "project_id", "event_id"], ["project_accounting_handoffs.tenant_id", "project_accounting_handoffs.organization_id", "project_accounting_handoffs.project_id", "project_accounting_handoffs.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "organization_id", "event_id", name="uq_pm_accounting_outbox_event"),
        sa.CheckConstraint("status IN ('pending', 'claimed', 'retry', 'published', 'dead_letter')", name="ck_pm_accounting_outbox_status"),
        sa.CheckConstraint("aggregate_version >= 1 AND version >= 1", name="ck_pm_accounting_outbox_versions"),
        sa.CheckConstraint("attempt_count >= 0 AND max_attempts >= 1 AND attempt_count <= max_attempts", name="ck_pm_accounting_outbox_attempts"),
    )
    for table in ("organization_accounting_connectors", "project_accounting_handoffs", "project_accounting_outbox"):
        enable_tenant_organization_rls(op, op.get_bind(), table)


def downgrade():
    for table in ("project_accounting_outbox", "project_accounting_handoffs", "organization_accounting_connectors"):
        op.drop_table(table)
