"""add inventory requisition tables

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
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
    if not _has_table("inventory_purchase_requisitions"):
        op.create_table(
            "inventory_purchase_requisitions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("requisition_number", sa.String(length=64), nullable=False),
            sa.Column("requesting_site_id", sa.String(), nullable=False),
            sa.Column("requesting_storeroom_id", sa.String(), nullable=False),
            sa.Column("requester_user_id", sa.String(), nullable=True),
            sa.Column("requester_username", sa.String(length=128), nullable=True),
            sa.Column(
                "status",
                sa.Enum(
                    "DRAFT",
                    "SUBMITTED",
                    "UNDER_REVIEW",
                    "APPROVED",
                    "REJECTED",
                    "PARTIALLY_SOURCED",
                    "FULLY_SOURCED",
                    "CANCELLED",
                    "CLOSED",
                    name="purchaserequisitionstatus",
                ),
                nullable=False,
                server_default="DRAFT",
            ),
            sa.Column("purpose", sa.Text(), nullable=True),
            sa.Column("needed_by_date", sa.Date(), nullable=True),
            sa.Column("priority", sa.String(length=32), nullable=True),
            sa.Column("approval_request_id", sa.String(), nullable=True),
            sa.Column("source_reference_type", sa.String(length=64), nullable=True),
            sa.Column("source_reference_id", sa.String(length=128), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["requesting_site_id"], ["sites.id"]),
            sa.ForeignKeyConstraint(["requesting_storeroom_id"], ["inventory_storerooms.id"]),
            sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "requisition_number", name="ux_inventory_requisitions_number"),
        )
    if not _has_table("inventory_purchase_requisition_lines"):
        op.create_table(
            "inventory_purchase_requisition_lines",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("purchase_requisition_id", sa.String(), nullable=False),
            sa.Column("line_number", sa.Integer(), nullable=False),
            sa.Column("stock_item_id", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("quantity_requested", sa.Float(), nullable=False),
            sa.Column("uom", sa.String(length=32), nullable=False),
            sa.Column("needed_by_date", sa.Date(), nullable=True),
            sa.Column("estimated_unit_cost", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("suggested_supplier_party_id", sa.String(), nullable=True),
            sa.Column(
                "status",
                sa.Enum(
                    "DRAFT",
                    "OPEN",
                    "REJECTED",
                    "CANCELLED",
                    "FULLY_SOURCED",
                    name="purchaserequisitionlinestatus",
                ),
                nullable=False,
                server_default="DRAFT",
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["purchase_requisition_id"], ["inventory_purchase_requisitions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stock_item_id"], ["inventory_stock_items.id"]),
            sa.ForeignKeyConstraint(["suggested_supplier_party_id"], ["parties.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "purchase_requisition_id",
                "line_number",
                name="ux_inventory_requisition_lines_number",
            ),
        )

    if not _has_index("inventory_purchase_requisitions", "idx_inventory_requisitions_org"):
        op.create_index("idx_inventory_requisitions_org", "inventory_purchase_requisitions", ["organization_id"], unique=False)
    if not _has_index("inventory_purchase_requisitions", "idx_inventory_requisitions_status"):
        op.create_index("idx_inventory_requisitions_status", "inventory_purchase_requisitions", ["status"], unique=False)
    if not _has_index("inventory_purchase_requisitions", "idx_inventory_requisitions_site"):
        op.create_index("idx_inventory_requisitions_site", "inventory_purchase_requisitions", ["requesting_site_id"], unique=False)
    if not _has_index("inventory_purchase_requisitions", "idx_inventory_requisitions_storeroom"):
        op.create_index(
            "idx_inventory_requisitions_storeroom",
            "inventory_purchase_requisitions",
            ["requesting_storeroom_id"],
            unique=False,
        )
    if not _has_index("inventory_purchase_requisition_lines", "idx_inventory_requisition_lines_requisition"):
        op.create_index(
            "idx_inventory_requisition_lines_requisition",
            "inventory_purchase_requisition_lines",
            ["purchase_requisition_id"],
            unique=False,
        )
    if not _has_index("inventory_purchase_requisition_lines", "idx_inventory_requisition_lines_item"):
        op.create_index(
            "idx_inventory_requisition_lines_item",
            "inventory_purchase_requisition_lines",
            ["stock_item_id"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("inventory_purchase_requisition_lines", "idx_inventory_requisition_lines_item"):
        op.drop_index("idx_inventory_requisition_lines_item", table_name="inventory_purchase_requisition_lines")
    if _has_index("inventory_purchase_requisition_lines", "idx_inventory_requisition_lines_requisition"):
        op.drop_index("idx_inventory_requisition_lines_requisition", table_name="inventory_purchase_requisition_lines")
    if _has_index("inventory_purchase_requisitions", "idx_inventory_requisitions_storeroom"):
        op.drop_index("idx_inventory_requisitions_storeroom", table_name="inventory_purchase_requisitions")
    if _has_index("inventory_purchase_requisitions", "idx_inventory_requisitions_site"):
        op.drop_index("idx_inventory_requisitions_site", table_name="inventory_purchase_requisitions")
    if _has_index("inventory_purchase_requisitions", "idx_inventory_requisitions_status"):
        op.drop_index("idx_inventory_requisitions_status", table_name="inventory_purchase_requisitions")
    if _has_index("inventory_purchase_requisitions", "idx_inventory_requisitions_org"):
        op.drop_index("idx_inventory_requisitions_org", table_name="inventory_purchase_requisitions")
    if _has_table("inventory_purchase_requisition_lines"):
        op.drop_table("inventory_purchase_requisition_lines")
    if _has_table("inventory_purchase_requisitions"):
        op.drop_table("inventory_purchase_requisitions")
