"""add inventory balance and transaction tables

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
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
    if not _has_table("inventory_stock_balances"):
        op.create_table(
            "inventory_stock_balances",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("stock_item_id", sa.String(), nullable=False),
            sa.Column("storeroom_id", sa.String(), nullable=False),
            sa.Column("uom", sa.String(length=32), nullable=False),
            sa.Column("on_hand_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("reserved_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("available_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("on_order_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("committed_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("average_cost", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("last_receipt_at", sa.DateTime(), nullable=True),
            sa.Column("last_issue_at", sa.DateTime(), nullable=True),
            sa.Column("reorder_required", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stock_item_id"], ["inventory_stock_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["storeroom_id"], ["inventory_storerooms.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "stock_item_id",
                "storeroom_id",
                name="ux_inventory_stock_balances_position",
            ),
        )
    if not _has_table("inventory_stock_transactions"):
        op.create_table(
            "inventory_stock_transactions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("transaction_number", sa.String(length=64), nullable=False),
            sa.Column("stock_item_id", sa.String(), nullable=False),
            sa.Column("storeroom_id", sa.String(), nullable=False),
            sa.Column(
                "transaction_type",
                sa.Enum("OPENING_BALANCE", "ADJUSTMENT_INCREASE", "ADJUSTMENT_DECREASE", name="stocktransactiontype"),
                nullable=False,
            ),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("uom", sa.String(length=32), nullable=False),
            sa.Column("unit_cost", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("transaction_at", sa.DateTime(), nullable=False),
            sa.Column("reference_type", sa.String(length=64), nullable=True),
            sa.Column("reference_id", sa.String(length=128), nullable=True),
            sa.Column("performed_by_user_id", sa.String(), nullable=True),
            sa.Column("performed_by_username", sa.String(length=128), nullable=True),
            sa.Column("resulting_on_hand_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("resulting_available_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stock_item_id"], ["inventory_stock_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["storeroom_id"], ["inventory_storerooms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["performed_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "transaction_number",
                name="ux_inventory_stock_transactions_number",
            ),
        )

    if not _has_index("inventory_stock_balances", "idx_inventory_stock_balances_org"):
        op.create_index("idx_inventory_stock_balances_org", "inventory_stock_balances", ["organization_id"], unique=False)
    if not _has_index("inventory_stock_balances", "idx_inventory_stock_balances_item"):
        op.create_index("idx_inventory_stock_balances_item", "inventory_stock_balances", ["stock_item_id"], unique=False)
    if not _has_index("inventory_stock_balances", "idx_inventory_stock_balances_storeroom"):
        op.create_index("idx_inventory_stock_balances_storeroom", "inventory_stock_balances", ["storeroom_id"], unique=False)
    if not _has_index("inventory_stock_transactions", "idx_inventory_stock_transactions_org"):
        op.create_index(
            "idx_inventory_stock_transactions_org",
            "inventory_stock_transactions",
            ["organization_id"],
            unique=False,
        )
    if not _has_index("inventory_stock_transactions", "idx_inventory_stock_transactions_item"):
        op.create_index(
            "idx_inventory_stock_transactions_item",
            "inventory_stock_transactions",
            ["stock_item_id"],
            unique=False,
        )
    if not _has_index("inventory_stock_transactions", "idx_inventory_stock_transactions_storeroom"):
        op.create_index(
            "idx_inventory_stock_transactions_storeroom",
            "inventory_stock_transactions",
            ["storeroom_id"],
            unique=False,
        )
    if not _has_index("inventory_stock_transactions", "idx_inventory_stock_transactions_at"):
        op.create_index(
            "idx_inventory_stock_transactions_at",
            "inventory_stock_transactions",
            ["transaction_at"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("inventory_stock_transactions", "idx_inventory_stock_transactions_at"):
        op.drop_index("idx_inventory_stock_transactions_at", table_name="inventory_stock_transactions")
    if _has_index("inventory_stock_transactions", "idx_inventory_stock_transactions_storeroom"):
        op.drop_index("idx_inventory_stock_transactions_storeroom", table_name="inventory_stock_transactions")
    if _has_index("inventory_stock_transactions", "idx_inventory_stock_transactions_item"):
        op.drop_index("idx_inventory_stock_transactions_item", table_name="inventory_stock_transactions")
    if _has_index("inventory_stock_transactions", "idx_inventory_stock_transactions_org"):
        op.drop_index("idx_inventory_stock_transactions_org", table_name="inventory_stock_transactions")
    if _has_index("inventory_stock_balances", "idx_inventory_stock_balances_storeroom"):
        op.drop_index("idx_inventory_stock_balances_storeroom", table_name="inventory_stock_balances")
    if _has_index("inventory_stock_balances", "idx_inventory_stock_balances_item"):
        op.drop_index("idx_inventory_stock_balances_item", table_name="inventory_stock_balances")
    if _has_index("inventory_stock_balances", "idx_inventory_stock_balances_org"):
        op.drop_index("idx_inventory_stock_balances_org", table_name="inventory_stock_balances")
    if _has_table("inventory_stock_transactions"):
        op.drop_table("inventory_stock_transactions")
    if _has_table("inventory_stock_balances"):
        op.drop_table("inventory_stock_balances")
