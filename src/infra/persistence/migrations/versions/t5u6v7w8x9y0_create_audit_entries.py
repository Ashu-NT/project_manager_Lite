"""Migration B: Create audit_entries table.

Revision ID: t5u6v7w8x9y0
Revises: s4t5u6v7w8x9
Create Date: 2026-06-14

Creates the audit_entries table with the full enterprise AuditEntry compliance schema.
This table is append-only — no UPDATE or DELETE operations should ever be issued against it.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "t5u6v7w8x9y0"
down_revision = "s4t5u6v7w8x9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("actor_type", sa.String(32), nullable=False, server_default="user"),
        sa.Column("actor_username", sa.String(128), nullable=True),
        sa.Column("actor_ip", sa.String(64), nullable=True),
        sa.Column("actor_user_agent", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("entity_parent_id", sa.String(), nullable=True),
        sa.Column("operation", sa.String(64), nullable=False),
        sa.Column("field", sa.String(128), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("module", sa.String(64), nullable=False, server_default="platform"),
        sa.Column(
            "tenant_id",
            sa.String(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("workspace_id", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="api"),
        sa.Column("severity", sa.String(16), nullable=False, server_default="low"),
        sa.Column("compliance_tag", sa.String(32), nullable=False, server_default="none"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_entries_tenant_ts", "audit_entries", ["tenant_id", "timestamp"])
    op.create_index("idx_audit_entries_org_ts", "audit_entries", ["organization_id", "timestamp"])
    op.create_index("idx_audit_entries_entity", "audit_entries", ["entity_type", "entity_id"])
    op.create_index("idx_audit_entries_actor", "audit_entries", ["actor_id", "timestamp"])
    op.create_index("idx_audit_entries_operation", "audit_entries", ["operation", "timestamp"])
    op.create_index("idx_audit_entries_compliance", "audit_entries", ["compliance_tag", "timestamp"])
    op.create_index("idx_audit_entries_severity", "audit_entries", ["severity", "timestamp"])


def downgrade() -> None:
    op.drop_index("idx_audit_entries_severity", table_name="audit_entries")
    op.drop_index("idx_audit_entries_compliance", table_name="audit_entries")
    op.drop_index("idx_audit_entries_operation", table_name="audit_entries")
    op.drop_index("idx_audit_entries_actor", table_name="audit_entries")
    op.drop_index("idx_audit_entries_entity", table_name="audit_entries")
    op.drop_index("idx_audit_entries_org_ts", table_name="audit_entries")
    op.drop_index("idx_audit_entries_tenant_ts", table_name="audit_entries")
    op.drop_table("audit_entries")
