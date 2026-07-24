"""Migration A: Create activity_entries table.

Revision ID: s4t5u6v7w8x9
Revises: r3s4t5u6v7w8
Create Date: 2026-06-14

Creates the activity_entries table with the full ActivityEntry schema including
tenant/org isolation, entity scoping, and all required indexes.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "s4t5u6v7w8x9"
down_revision = "r3s4t5u6v7w8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activity_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("actor_role", sa.String(64), nullable=True),
        sa.Column("module", sa.String(64), nullable=False, server_default="platform"),
        sa.Column("workspace_id", sa.String(), nullable=True),
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
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("type", sa.String(32), nullable=False, server_default="info"),
        sa.Column("human_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("context_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("parent_entity_id", sa.String(), nullable=True),
        sa.Column("icon", sa.String(64), nullable=True),
        sa.Column("color", sa.String(32), nullable=True),
        sa.Column("visibility", sa.String(32), nullable=False, server_default="workspace"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_activity_tenant_timestamp", "activity_entries", ["tenant_id", "timestamp"])
    op.create_index("idx_activity_org_timestamp", "activity_entries", ["organization_id", "timestamp"])
    op.create_index("idx_activity_entity", "activity_entries", ["entity_type", "entity_id"])
    op.create_index("idx_activity_workspace", "activity_entries", ["workspace_id", "timestamp"])
    op.create_index("idx_activity_module_entity", "activity_entries", ["module", "entity_type", "entity_id"])
    op.create_index("idx_activity_actor", "activity_entries", ["actor_id", "timestamp"])


def downgrade() -> None:
    op.drop_index("idx_activity_actor", table_name="activity_entries")
    op.drop_index("idx_activity_module_entity", table_name="activity_entries")
    op.drop_index("idx_activity_workspace", table_name="activity_entries")
    op.drop_index("idx_activity_entity", table_name="activity_entries")
    op.drop_index("idx_activity_org_timestamp", table_name="activity_entries")
    op.drop_index("idx_activity_tenant_timestamp", table_name="activity_entries")
    op.drop_table("activity_entries")
