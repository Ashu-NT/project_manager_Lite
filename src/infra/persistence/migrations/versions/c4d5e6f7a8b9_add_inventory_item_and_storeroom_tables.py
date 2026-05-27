"""add inventory item and storeroom tables

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
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
    if not _has_table("inventory_stock_items"):
        op.create_table(
            "inventory_stock_items",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("item_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("item_type", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
            sa.Column("stock_uom", sa.String(length=32), nullable=False),
            sa.Column("order_uom", sa.String(length=32), nullable=False),
            sa.Column("issue_uom", sa.String(length=32), nullable=False),
            sa.Column("category_code", sa.String(length=64), nullable=True),
            sa.Column("commodity_code", sa.String(length=64), nullable=True),
            sa.Column("is_stocked", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("is_purchase_allowed", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("default_reorder_policy", sa.String(length=64), nullable=True),
            sa.Column("min_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("max_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("reorder_point", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("reorder_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("lead_time_days", sa.Integer(), nullable=True),
            sa.Column("is_lot_tracked", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("is_serial_tracked", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("shelf_life_days", sa.Integer(), nullable=True),
            sa.Column("preferred_party_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["preferred_party_id"], ["parties.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "item_code", name="ux_inventory_stock_items_org_code"),
        )
    if not _has_table("inventory_storerooms"):
        op.create_table(
            "inventory_storerooms",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("storeroom_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("site_id", sa.String(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
            sa.Column("storeroom_type", sa.String(length=64), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("is_internal_supplier", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("allows_issue", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("allows_transfer", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("allows_receiving", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("default_currency_code", sa.String(length=8), nullable=True),
            sa.Column("manager_party_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
            sa.ForeignKeyConstraint(["manager_party_id"], ["parties.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "storeroom_code", name="ux_inventory_storerooms_org_code"),
        )

    if not _has_index("inventory_stock_items", "idx_inventory_stock_items_org"):
        op.create_index("idx_inventory_stock_items_org", "inventory_stock_items", ["organization_id"], unique=False)
    if not _has_index("inventory_stock_items", "idx_inventory_stock_items_active"):
        op.create_index("idx_inventory_stock_items_active", "inventory_stock_items", ["is_active"], unique=False)
    if not _has_index("inventory_storerooms", "idx_inventory_storerooms_org"):
        op.create_index("idx_inventory_storerooms_org", "inventory_storerooms", ["organization_id"], unique=False)
    if not _has_index("inventory_storerooms", "idx_inventory_storerooms_site"):
        op.create_index("idx_inventory_storerooms_site", "inventory_storerooms", ["site_id"], unique=False)
    if not _has_index("inventory_storerooms", "idx_inventory_storerooms_active"):
        op.create_index("idx_inventory_storerooms_active", "inventory_storerooms", ["is_active"], unique=False)


def downgrade() -> None:
    if _has_index("inventory_storerooms", "idx_inventory_storerooms_active"):
        op.drop_index("idx_inventory_storerooms_active", table_name="inventory_storerooms")
    if _has_index("inventory_storerooms", "idx_inventory_storerooms_site"):
        op.drop_index("idx_inventory_storerooms_site", table_name="inventory_storerooms")
    if _has_index("inventory_storerooms", "idx_inventory_storerooms_org"):
        op.drop_index("idx_inventory_storerooms_org", table_name="inventory_storerooms")
    if _has_index("inventory_stock_items", "idx_inventory_stock_items_active"):
        op.drop_index("idx_inventory_stock_items_active", table_name="inventory_stock_items")
    if _has_index("inventory_stock_items", "idx_inventory_stock_items_org"):
        op.drop_index("idx_inventory_stock_items_org", table_name="inventory_stock_items")
    if _has_table("inventory_storerooms"):
        op.drop_table("inventory_storerooms")
    if _has_table("inventory_stock_items"):
        op.drop_table("inventory_stock_items")
