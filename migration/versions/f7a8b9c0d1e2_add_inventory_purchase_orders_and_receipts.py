"""add inventory purchase orders and receipts

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
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


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def upgrade() -> None:
    if _has_table("inventory_purchase_requisition_lines") and not _has_column(
        "inventory_purchase_requisition_lines",
        "quantity_sourced",
    ):
        with op.batch_alter_table("inventory_purchase_requisition_lines") as batch_op:
            batch_op.add_column(
                sa.Column("quantity_sourced", sa.Float(), nullable=False, server_default="0.0")
            )

    if not _has_table("inventory_purchase_orders"):
        op.create_table(
            "inventory_purchase_orders",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("po_number", sa.String(length=64), nullable=False),
            sa.Column("site_id", sa.String(), nullable=False),
            sa.Column("supplier_party_id", sa.String(), nullable=False),
            sa.Column(
                "status",
                sa.Enum(
                    "DRAFT",
                    "SUBMITTED",
                    "UNDER_REVIEW",
                    "APPROVED",
                    "REJECTED",
                    "SENT",
                    "PARTIALLY_RECEIVED",
                    "FULLY_RECEIVED",
                    "CLOSED",
                    "CANCELLED",
                    name="purchaseorderstatus",
                ),
                nullable=False,
                server_default="DRAFT",
            ),
            sa.Column("order_date", sa.Date(), nullable=True),
            sa.Column("expected_delivery_date", sa.Date(), nullable=True),
            sa.Column("currency_code", sa.String(length=16), nullable=True),
            sa.Column("approval_request_id", sa.String(), nullable=True),
            sa.Column("source_requisition_id", sa.String(), nullable=True),
            sa.Column("supplier_reference", sa.String(length=128), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("sent_at", sa.DateTime(), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
            sa.ForeignKeyConstraint(["supplier_party_id"], ["parties.id"]),
            sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["source_requisition_id"], ["inventory_purchase_requisitions.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "po_number", name="ux_inventory_purchase_orders_number"),
        )

    if not _has_table("inventory_purchase_order_lines"):
        op.create_table(
            "inventory_purchase_order_lines",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("purchase_order_id", sa.String(), nullable=False),
            sa.Column("line_number", sa.Integer(), nullable=False),
            sa.Column("stock_item_id", sa.String(), nullable=False),
            sa.Column("destination_storeroom_id", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("quantity_ordered", sa.Float(), nullable=False),
            sa.Column("quantity_received", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("quantity_rejected", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("uom", sa.String(length=32), nullable=False),
            sa.Column("unit_price", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("expected_delivery_date", sa.Date(), nullable=True),
            sa.Column("source_requisition_line_id", sa.String(), nullable=True),
            sa.Column(
                "status",
                sa.Enum(
                    "DRAFT",
                    "OPEN",
                    "PARTIALLY_RECEIVED",
                    "FULLY_RECEIVED",
                    "CANCELLED",
                    name="purchaseorderlinestatus",
                ),
                nullable=False,
                server_default="DRAFT",
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["purchase_order_id"], ["inventory_purchase_orders.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stock_item_id"], ["inventory_stock_items.id"]),
            sa.ForeignKeyConstraint(["destination_storeroom_id"], ["inventory_storerooms.id"]),
            sa.ForeignKeyConstraint(["source_requisition_line_id"], ["inventory_purchase_requisition_lines.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("purchase_order_id", "line_number", name="ux_inventory_purchase_order_lines_number"),
        )

    if not _has_table("inventory_receipt_headers"):
        op.create_table(
            "inventory_receipt_headers",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("receipt_number", sa.String(length=64), nullable=False),
            sa.Column("purchase_order_id", sa.String(), nullable=False),
            sa.Column("received_site_id", sa.String(), nullable=False),
            sa.Column("supplier_party_id", sa.String(), nullable=False),
            sa.Column(
                "status",
                sa.Enum("POSTED", name="receiptstatus"),
                nullable=False,
                server_default="POSTED",
            ),
            sa.Column("receipt_date", sa.DateTime(), nullable=False),
            sa.Column("supplier_delivery_reference", sa.String(length=128), nullable=True),
            sa.Column("received_by_user_id", sa.String(), nullable=True),
            sa.Column("received_by_username", sa.String(length=128), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["purchase_order_id"], ["inventory_purchase_orders.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["received_site_id"], ["sites.id"]),
            sa.ForeignKeyConstraint(["supplier_party_id"], ["parties.id"]),
            sa.ForeignKeyConstraint(["received_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "receipt_number", name="ux_inventory_receipt_headers_number"),
        )

    if not _has_table("inventory_receipt_lines"):
        op.create_table(
            "inventory_receipt_lines",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("receipt_header_id", sa.String(), nullable=False),
            sa.Column("purchase_order_line_id", sa.String(), nullable=False),
            sa.Column("line_number", sa.Integer(), nullable=False),
            sa.Column("stock_item_id", sa.String(), nullable=False),
            sa.Column("storeroom_id", sa.String(), nullable=False),
            sa.Column("quantity_accepted", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("quantity_rejected", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("uom", sa.String(length=32), nullable=False),
            sa.Column("unit_cost", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["receipt_header_id"], ["inventory_receipt_headers.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["purchase_order_line_id"], ["inventory_purchase_order_lines.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stock_item_id"], ["inventory_stock_items.id"]),
            sa.ForeignKeyConstraint(["storeroom_id"], ["inventory_storerooms.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("receipt_header_id", "line_number", name="ux_inventory_receipt_lines_number"),
        )

    index_specs = (
        ("inventory_purchase_orders", "idx_inventory_purchase_orders_org", ["organization_id"]),
        ("inventory_purchase_orders", "idx_inventory_purchase_orders_status", ["status"]),
        ("inventory_purchase_orders", "idx_inventory_purchase_orders_site", ["site_id"]),
        ("inventory_purchase_orders", "idx_inventory_purchase_orders_supplier", ["supplier_party_id"]),
        ("inventory_purchase_order_lines", "idx_inventory_purchase_order_lines_order", ["purchase_order_id"]),
        ("inventory_purchase_order_lines", "idx_inventory_purchase_order_lines_item", ["stock_item_id"]),
        ("inventory_purchase_order_lines", "idx_inventory_purchase_order_lines_storeroom", ["destination_storeroom_id"]),
        ("inventory_purchase_order_lines", "idx_inventory_purchase_order_lines_req_line", ["source_requisition_line_id"]),
        ("inventory_receipt_headers", "idx_inventory_receipt_headers_org", ["organization_id"]),
        ("inventory_receipt_headers", "idx_inventory_receipt_headers_order", ["purchase_order_id"]),
        ("inventory_receipt_headers", "idx_inventory_receipt_headers_date", ["receipt_date"]),
        ("inventory_receipt_lines", "idx_inventory_receipt_lines_receipt", ["receipt_header_id"]),
        ("inventory_receipt_lines", "idx_inventory_receipt_lines_po_line", ["purchase_order_line_id"]),
    )
    for table_name, index_name, columns in index_specs:
        if not _has_index(table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    index_specs = (
        ("inventory_receipt_lines", "idx_inventory_receipt_lines_po_line"),
        ("inventory_receipt_lines", "idx_inventory_receipt_lines_receipt"),
        ("inventory_receipt_headers", "idx_inventory_receipt_headers_date"),
        ("inventory_receipt_headers", "idx_inventory_receipt_headers_order"),
        ("inventory_receipt_headers", "idx_inventory_receipt_headers_org"),
        ("inventory_purchase_order_lines", "idx_inventory_purchase_order_lines_req_line"),
        ("inventory_purchase_order_lines", "idx_inventory_purchase_order_lines_storeroom"),
        ("inventory_purchase_order_lines", "idx_inventory_purchase_order_lines_item"),
        ("inventory_purchase_order_lines", "idx_inventory_purchase_order_lines_order"),
        ("inventory_purchase_orders", "idx_inventory_purchase_orders_supplier"),
        ("inventory_purchase_orders", "idx_inventory_purchase_orders_site"),
        ("inventory_purchase_orders", "idx_inventory_purchase_orders_status"),
        ("inventory_purchase_orders", "idx_inventory_purchase_orders_org"),
    )
    for table_name, index_name in index_specs:
        if _has_index(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
    if _has_table("inventory_receipt_lines"):
        op.drop_table("inventory_receipt_lines")
    if _has_table("inventory_receipt_headers"):
        op.drop_table("inventory_receipt_headers")
    if _has_table("inventory_purchase_order_lines"):
        op.drop_table("inventory_purchase_order_lines")
    if _has_table("inventory_purchase_orders"):
        op.drop_table("inventory_purchase_orders")
    if _has_table("inventory_purchase_requisition_lines") and _has_column(
        "inventory_purchase_requisition_lines",
        "quantity_sourced",
    ):
        with op.batch_alter_table("inventory_purchase_requisition_lines") as batch_op:
            batch_op.drop_column("quantity_sourced")
