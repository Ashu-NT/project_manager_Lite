"""Add organization_id to user_roles to support org-scoped role assignments.

Revision ID: x8y9z0a1b2c3
Revises: w7x8y9z0a1b2
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "x8y9z0a1b2c3"
down_revision = "w7x8y9z0a1b2"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not _table_exists(inspector, "user_roles"):
        return

    columns = _column_names(inspector, "user_roles")
    if "organization_id" not in columns:
        op.add_column(
            "user_roles",
            sa.Column(
                "organization_id",
                sa.String(),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=True,
            ),
        )

    inspector = sa.inspect(connection)
    if "idx_user_roles_organization" not in _index_names(inspector, "user_roles"):
        op.create_index("idx_user_roles_organization", "user_roles", ["organization_id"])


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "user_roles"):
        return
    if "idx_user_roles_organization" in _index_names(inspector, "user_roles"):
        op.drop_index("idx_user_roles_organization", table_name="user_roles")
    inspector = sa.inspect(connection)
    if "organization_id" in _column_names(inspector, "user_roles"):
        with op.batch_alter_table("user_roles") as batch_op:
            batch_op.drop_column("organization_id")
