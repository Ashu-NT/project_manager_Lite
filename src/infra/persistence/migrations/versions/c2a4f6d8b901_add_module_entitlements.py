"""add module entitlements

Revision ID: c2a4f6d8b901
Revises: 9f1a2c6b4e11
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa


revision = "c2a4f6d8b901"
down_revision = "9f1a2c6b4e11"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def upgrade() -> None:
    if _has_table("module_entitlements"):
        return
    op.create_table(
        "module_entitlements",
        sa.Column("module_code", sa.String(length=128), nullable=False),
        sa.Column("licensed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("module_code"),
    )


def downgrade() -> None:
    if _has_table("module_entitlements"):
        op.drop_table("module_entitlements")
