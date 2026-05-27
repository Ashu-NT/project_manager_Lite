"""add inventory item uom ratio columns

Revision ID: 1b2c3d4e5f6a
Revises: 0a1b2c3d4e5f
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "1b2c3d4e5f6a"
down_revision = "0a1b2c3d4e5f"
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
    if not _has_table("inventory_stock_items"):
        return
    with op.batch_alter_table("inventory_stock_items") as batch:
        if not _has_column("inventory_stock_items", "order_uom_ratio"):
            batch.add_column(
                sa.Column(
                    "order_uom_ratio",
                    sa.Float(),
                    nullable=False,
                    server_default=sa.text("1.0"),
                )
            )
        if not _has_column("inventory_stock_items", "issue_uom_ratio"):
            batch.add_column(
                sa.Column(
                    "issue_uom_ratio",
                    sa.Float(),
                    nullable=False,
                    server_default=sa.text("1.0"),
                )
            )


def downgrade() -> None:
    if not _has_table("inventory_stock_items"):
        return
    with op.batch_alter_table("inventory_stock_items") as batch:
        if _has_column("inventory_stock_items", "issue_uom_ratio"):
            batch.drop_column("issue_uom_ratio")
        if _has_column("inventory_stock_items", "order_uom_ratio"):
            batch.drop_column("order_uom_ratio")
