"""Create platform_events table.

Revision ID: z3a4b5c6d7e8
Revises: y2z3a4b5c6d7
Create Date: 2026-06-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "z3a4b5c6d7e8"
down_revision = "y2z3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("operation", sa.String(64), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=True),
        sa.Column(
            "tenant_id",
            sa.String(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False, server_default="success"),
        sa.Column("severity", sa.String(16), nullable=False, server_default="low"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_platform_events_tenant", "platform_events", ["tenant_id", "created_at"])
    op.create_index("idx_platform_events_actor", "platform_events", ["actor_user_id", "created_at"])
    op.create_index("idx_platform_events_resource", "platform_events", ["tenant_id", "resource_type", "resource_id"])
    op.create_index("idx_platform_events_operation", "platform_events", ["operation", "created_at"])
    op.create_index("idx_platform_events_created_at", "platform_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_platform_events_created_at", table_name="platform_events")
    op.drop_index("idx_platform_events_operation", table_name="platform_events")
    op.drop_index("idx_platform_events_resource", table_name="platform_events")
    op.drop_index("idx_platform_events_actor", table_name="platform_events")
    op.drop_index("idx_platform_events_tenant", table_name="platform_events")
    op.drop_table("platform_events")
