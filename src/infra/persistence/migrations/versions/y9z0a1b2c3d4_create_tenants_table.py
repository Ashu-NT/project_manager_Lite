"""Create tenants table — top-level SaaS isolation boundary.

Revision ID: y9z0a1b2c3d4
Revises: x8y9z0a1b2c3
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "y9z0a1b2c3d4"
down_revision = "x8y9z0a1b2c3"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not _table_exists(inspector, "tenants"):
        op.create_table(
            "tenants",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("tenant_code", sa.String(64), nullable=False, unique=True),
            sa.Column("display_name", sa.String(256), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )

    inspector = sa.inspect(connection)
    existing_indexes = _index_names(inspector, "tenants")
    if "idx_tenants_code" not in existing_indexes:
        op.create_index("idx_tenants_code", "tenants", ["tenant_code"], unique=True)
    if "idx_tenants_active" not in existing_indexes:
        op.create_index("idx_tenants_active", "tenants", ["is_active"])


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "tenants"):
        return
    for idx in ("idx_tenants_active", "idx_tenants_code"):
        if idx in _index_names(inspector, "tenants"):
            op.drop_index(idx, table_name="tenants")
    op.drop_table("tenants")
