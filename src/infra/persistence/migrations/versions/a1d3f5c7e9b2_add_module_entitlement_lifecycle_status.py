"""add module entitlement lifecycle status

Revision ID: a1d3f5c7e9b2
Revises: f6a2c1d9b4e7
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa


revision = "a1d3f5c7e9b2"
down_revision = "f6a2c1d9b4e7"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def upgrade() -> None:
    table_name = "organization_module_entitlements"
    if not _has_table(table_name):
        return
    if not _has_column(table_name, "lifecycle_status"):
        op.add_column(
            table_name,
            sa.Column(
                "lifecycle_status",
                sa.String(length=32),
                nullable=False,
                server_default="inactive",
            ),
        )
    bind = op.get_bind()
    bind.execute(
        sa.text(
            f"UPDATE {table_name} "
            "SET lifecycle_status = CASE "
            "WHEN licensed = 1 THEN 'active' "
            "ELSE 'inactive' "
            "END "
            "WHERE lifecycle_status IS NULL OR lifecycle_status = '' OR lifecycle_status = 'inactive'"
        )
    )


def downgrade() -> None:
    table_name = "organization_module_entitlements"
    if not _has_column(table_name, "lifecycle_status"):
        return
    with op.batch_alter_table(table_name) as batch:
        batch.drop_column("lifecycle_status")
