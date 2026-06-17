"""Create user_tenants table — explicit user-to-tenant membership boundary.

Revision ID: x1y2z3a4b5c6
Revises: w8x9y0z1a2b3
Create Date: 2026-06-17

Adds user_tenants (user_id, tenant_id, is_active, tenant_role, timestamps).
Backfills all existing users into the default (first active) tenant.
The bootstrap admin user is always exempt from membership checks via role,
so the backfill is a safety net for future non-admin users.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op


revision = "x1y2z3a4b5c6"
down_revision = "w8x9y0z1a2b3"
branch_labels = None
depends_on = None

_NOW = "2026-06-17T00:00:00"


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not _table_exists(inspector, "user_tenants"):
        op.create_table(
            "user_tenants",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column(
                "user_id",
                sa.String(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "tenant_id",
                sa.String(),
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column(
                "tenant_role",
                sa.String(64),
                nullable=False,
                server_default="member",
            ),
            sa.Column("invited_at", sa.DateTime(), nullable=True),
            sa.Column("joined_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "tenant_id", name="ux_user_tenants_user_tenant"),
        )

    inspector = sa.inspect(connection)
    existing_indexes = _index_names(inspector, "user_tenants")
    if "idx_user_tenants_user" not in existing_indexes:
        op.create_index("idx_user_tenants_user", "user_tenants", ["user_id"])
    if "idx_user_tenants_tenant" not in existing_indexes:
        op.create_index("idx_user_tenants_tenant", "user_tenants", ["tenant_id"])
    if "idx_user_tenants_active" not in existing_indexes:
        op.create_index("idx_user_tenants_active", "user_tenants", ["is_active"])

    # Backfill: assign all existing users to the default (first active) tenant.
    if not _table_exists(inspector, "tenants") or not _table_exists(inspector, "users"):
        return

    default_tenant_row = connection.execute(
        sa.text(
            "SELECT id FROM tenants WHERE is_active = 1 ORDER BY tenant_code ASC LIMIT 1"
        )
    ).first()
    if default_tenant_row is None:
        return

    default_tenant_id = str(default_tenant_row[0])

    users = connection.execute(sa.text("SELECT id FROM users")).fetchall()
    for user_row in users:
        user_id = str(user_row[0])
        existing = connection.execute(
            sa.text(
                "SELECT id FROM user_tenants WHERE user_id = :uid AND tenant_id = :tid"
            ),
            {"uid": user_id, "tid": default_tenant_id},
        ).first()
        if existing is None:
            connection.execute(
                sa.text(
                    "INSERT INTO user_tenants "
                    "(id, user_id, tenant_id, is_active, tenant_role, invited_at, joined_at, created_at, updated_at) "
                    "VALUES (:id, :uid, :tid, 1, 'member', NULL, :now, :now, :now)"
                ),
                {"id": str(uuid.uuid4()), "uid": user_id, "tid": default_tenant_id, "now": _NOW},
            )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "user_tenants"):
        return
    for idx in ("idx_user_tenants_active", "idx_user_tenants_tenant", "idx_user_tenants_user"):
        if idx in _index_names(inspector, "user_tenants"):
            op.drop_index(idx, table_name="user_tenants")
    op.drop_table("user_tenants")
