"""add organizations table

Revision ID: e3b7d9a4c112
Revises: c2a4f6d8b901
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa


revision = "e3b7d9a4c112"
down_revision = "c2a4f6d8b901"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def upgrade() -> None:
    if not _has_table("organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_code", sa.String(length=64), nullable=False),
            sa.Column("display_name", sa.String(length=256), nullable=False),
            sa.Column("timezone_name", sa.String(length=128), nullable=False, server_default="UTC"),
            sa.Column("base_currency", sa.String(length=8), nullable=False, server_default="EUR"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_code"),
        )
    if not _has_index("organizations", "idx_organizations_code"):
        op.create_index("idx_organizations_code", "organizations", ["organization_code"], unique=True)
    if not _has_index("organizations", "idx_organizations_active"):
        op.create_index("idx_organizations_active", "organizations", ["is_active"], unique=False)


def downgrade() -> None:
    if _has_index("organizations", "idx_organizations_active"):
        op.drop_index("idx_organizations_active", table_name="organizations")
    if _has_index("organizations", "idx_organizations_code"):
        op.drop_index("idx_organizations_code", table_name="organizations")
    if _has_table("organizations"):
        op.drop_table("organizations")
