"""add inventory reservations

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "a8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
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
    if _has_table("inventory_stock_transactions"):
        with op.batch_alter_table("inventory_stock_transactions") as batch_op:
            batch_op.alter_column(
                "transaction_type",
                existing_type=sa.Enum(
                    "OPENING_BALANCE",
                    "ADJUSTMENT_INCREASE",
                    "ADJUSTMENT_DECREASE",
                    name="stocktransactiontype",
                ),
                type_=sa.Enum(
                    "OPENING_BALANCE",
                    "ADJUSTMENT_INCREASE",
                    "ADJUSTMENT_DECREASE",
                    "RESERVATION_HOLD",
                    "RESERVATION_RELEASE",
                    name="stocktransactiontype",
                ),
                existing_nullable=False,
            )
    if _has_table("inventory_purchase_requisition_lines"):
        with op.batch_alter_table("inventory_purchase_requisition_lines") as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=sa.Enum(
                    "DRAFT",
                    "OPEN",
                    "REJECTED",
                    "CANCELLED",
                    "FULLY_SOURCED",
                    name="purchaserequisitionlinestatus",
                ),
                type_=sa.Enum(
                    "DRAFT",
                    "OPEN",
                    "PARTIALLY_SOURCED",
                    "REJECTED",
                    "CANCELLED",
                    "FULLY_SOURCED",
                    name="purchaserequisitionlinestatus",
                ),
                existing_nullable=False,
            )

    if not _has_table("inventory_stock_reservations"):
        op.create_table(
            "inventory_stock_reservations",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("reservation_number", sa.String(length=64), nullable=False),
            sa.Column("stock_item_id", sa.String(), nullable=False),
            sa.Column("storeroom_id", sa.String(), nullable=False),
            sa.Column("reserved_qty", sa.Float(), nullable=False),
            sa.Column("issued_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("remaining_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("uom", sa.String(length=32), nullable=False),
            sa.Column(
                "status",
                sa.Enum(
                    "ACTIVE",
                    "PARTIALLY_ISSUED",
                    "FULLY_ISSUED",
                    "RELEASED",
                    "CANCELLED",
                    name="stockreservationstatus",
                ),
                nullable=False,
                server_default="ACTIVE",
            ),
            sa.Column("need_by_date", sa.Date(), nullable=True),
            sa.Column("source_reference_type", sa.String(length=64), nullable=True),
            sa.Column("source_reference_id", sa.String(length=128), nullable=True),
            sa.Column("requested_by_user_id", sa.String(), nullable=True),
            sa.Column("requested_by_username", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("released_at", sa.DateTime(), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stock_item_id"], ["inventory_stock_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["storeroom_id"], ["inventory_storerooms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "reservation_number",
                name="ux_inventory_stock_reservations_number",
            ),
        )

    if not _has_index("inventory_stock_reservations", "idx_inventory_stock_reservations_org"):
        op.create_index(
            "idx_inventory_stock_reservations_org",
            "inventory_stock_reservations",
            ["organization_id"],
            unique=False,
        )
    if not _has_index("inventory_stock_reservations", "idx_inventory_stock_reservations_item"):
        op.create_index(
            "idx_inventory_stock_reservations_item",
            "inventory_stock_reservations",
            ["stock_item_id"],
            unique=False,
        )
    if not _has_index("inventory_stock_reservations", "idx_inventory_stock_reservations_storeroom"):
        op.create_index(
            "idx_inventory_stock_reservations_storeroom",
            "inventory_stock_reservations",
            ["storeroom_id"],
            unique=False,
        )
    if not _has_index("inventory_stock_reservations", "idx_inventory_stock_reservations_status"):
        op.create_index(
            "idx_inventory_stock_reservations_status",
            "inventory_stock_reservations",
            ["status"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("inventory_stock_reservations", "idx_inventory_stock_reservations_status"):
        op.drop_index("idx_inventory_stock_reservations_status", table_name="inventory_stock_reservations")
    if _has_index("inventory_stock_reservations", "idx_inventory_stock_reservations_storeroom"):
        op.drop_index("idx_inventory_stock_reservations_storeroom", table_name="inventory_stock_reservations")
    if _has_index("inventory_stock_reservations", "idx_inventory_stock_reservations_item"):
        op.drop_index("idx_inventory_stock_reservations_item", table_name="inventory_stock_reservations")
    if _has_index("inventory_stock_reservations", "idx_inventory_stock_reservations_org"):
        op.drop_index("idx_inventory_stock_reservations_org", table_name="inventory_stock_reservations")
    if _has_table("inventory_stock_reservations"):
        op.drop_table("inventory_stock_reservations")

    if _has_table("inventory_purchase_requisition_lines"):
        with op.batch_alter_table("inventory_purchase_requisition_lines") as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=sa.Enum(
                    "DRAFT",
                    "OPEN",
                    "PARTIALLY_SOURCED",
                    "REJECTED",
                    "CANCELLED",
                    "FULLY_SOURCED",
                    name="purchaserequisitionlinestatus",
                ),
                type_=sa.Enum(
                    "DRAFT",
                    "OPEN",
                    "REJECTED",
                    "CANCELLED",
                    "FULLY_SOURCED",
                    name="purchaserequisitionlinestatus",
                ),
                existing_nullable=False,
            )
    if _has_table("inventory_stock_transactions"):
        with op.batch_alter_table("inventory_stock_transactions") as batch_op:
            batch_op.alter_column(
                "transaction_type",
                existing_type=sa.Enum(
                    "OPENING_BALANCE",
                    "ADJUSTMENT_INCREASE",
                    "ADJUSTMENT_DECREASE",
                    "RESERVATION_HOLD",
                    "RESERVATION_RELEASE",
                    name="stocktransactiontype",
                ),
                type_=sa.Enum(
                    "OPENING_BALANCE",
                    "ADJUSTMENT_INCREASE",
                    "ADJUSTMENT_DECREASE",
                    name="stocktransactiontype",
                ),
                existing_nullable=False,
            )
