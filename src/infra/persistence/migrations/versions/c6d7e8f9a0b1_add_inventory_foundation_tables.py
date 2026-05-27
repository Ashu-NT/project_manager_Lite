"""add inventory foundation tables

Revision ID: c6d7e8f9a0b1
Revises: b1c2d3e4f5a6
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa


revision = "c6d7e8f9a0b1"
down_revision = "b1c2d3e4f5a6"
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
    if not _has_table("inventory_storage_locations"):
        op.create_table(
            "inventory_storage_locations",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("storeroom_id", sa.String(), nullable=False),
            sa.Column("location_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("parent_location_id", sa.String(), nullable=True),
            sa.Column(
                "location_type",
                sa.Enum(
                    "ZONE",
                    "BIN",
                    "SHELF",
                    "STAGING",
                    "RECEIVING",
                    "ISSUE_POINT",
                    name="storagelocationtype",
                ),
                nullable=False,
                server_default="BIN",
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("is_quarantine", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("allows_issue", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("allows_putaway", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["storeroom_id"], ["inventory_storerooms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["parent_location_id"],
                ["inventory_storage_locations.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "storeroom_id",
                "location_code",
                name="ux_inventory_storage_locations_scope_code",
            ),
        )

    if not _has_table("inventory_reorder_policies"):
        op.create_table(
            "inventory_reorder_policies",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("stock_item_id", sa.String(), nullable=False),
            sa.Column("storeroom_id", sa.String(), nullable=False),
            sa.Column("location_id", sa.String(), nullable=True),
            sa.Column("policy_name", sa.String(length=128), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("min_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("max_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("reorder_point", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("reorder_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("economic_order_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("lead_time_days", sa.Integer(), nullable=True),
            sa.Column("review_period_days", sa.Integer(), nullable=True),
            sa.Column("preferred_supplier_party_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stock_item_id"], ["inventory_stock_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["storeroom_id"], ["inventory_storerooms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["location_id"],
                ["inventory_storage_locations.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["preferred_supplier_party_id"],
                ["parties.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "stock_item_id",
                "storeroom_id",
                "location_id",
                name="ux_inventory_reorder_policies_scope",
            ),
        )

    if not _has_table("inventory_cycle_counts"):
        op.create_table(
            "inventory_cycle_counts",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("cycle_count_number", sa.String(length=64), nullable=False),
            sa.Column("stock_item_id", sa.String(), nullable=False),
            sa.Column("storeroom_id", sa.String(), nullable=False),
            sa.Column("location_id", sa.String(), nullable=True),
            sa.Column("scheduled_count_date", sa.Date(), nullable=True),
            sa.Column(
                "status",
                sa.Enum(
                    "PLANNED",
                    "IN_PROGRESS",
                    "COMPLETED",
                    "CANCELLED",
                    name="cyclecountstatus",
                ),
                nullable=False,
                server_default="PLANNED",
            ),
            sa.Column("expected_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("counted_qty", sa.Float(), nullable=True),
            sa.Column("variance_qty", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("counted_by_user_id", sa.String(), nullable=True),
            sa.Column("counted_by_username", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stock_item_id"], ["inventory_stock_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["storeroom_id"], ["inventory_storerooms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["location_id"],
                ["inventory_storage_locations.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["counted_by_user_id"],
                ["users.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "cycle_count_number",
                name="ux_inventory_cycle_counts_number",
            ),
        )

    if not _has_index("inventory_storage_locations", "idx_inventory_storage_locations_org"):
        op.create_index(
            "idx_inventory_storage_locations_org",
            "inventory_storage_locations",
            ["organization_id"],
            unique=False,
        )
    if not _has_index("inventory_storage_locations", "idx_inventory_storage_locations_storeroom"):
        op.create_index(
            "idx_inventory_storage_locations_storeroom",
            "inventory_storage_locations",
            ["storeroom_id"],
            unique=False,
        )
    if not _has_index("inventory_storage_locations", "idx_inventory_storage_locations_parent"):
        op.create_index(
            "idx_inventory_storage_locations_parent",
            "inventory_storage_locations",
            ["parent_location_id"],
            unique=False,
        )
    if not _has_index("inventory_storage_locations", "idx_inventory_storage_locations_active"):
        op.create_index(
            "idx_inventory_storage_locations_active",
            "inventory_storage_locations",
            ["is_active"],
            unique=False,
        )
    if not _has_index("inventory_reorder_policies", "idx_inventory_reorder_policies_org"):
        op.create_index(
            "idx_inventory_reorder_policies_org",
            "inventory_reorder_policies",
            ["organization_id"],
            unique=False,
        )
    if not _has_index("inventory_reorder_policies", "idx_inventory_reorder_policies_item"):
        op.create_index(
            "idx_inventory_reorder_policies_item",
            "inventory_reorder_policies",
            ["stock_item_id"],
            unique=False,
        )
    if not _has_index("inventory_reorder_policies", "idx_inventory_reorder_policies_storeroom"):
        op.create_index(
            "idx_inventory_reorder_policies_storeroom",
            "inventory_reorder_policies",
            ["storeroom_id"],
            unique=False,
        )
    if not _has_index("inventory_reorder_policies", "idx_inventory_reorder_policies_location"):
        op.create_index(
            "idx_inventory_reorder_policies_location",
            "inventory_reorder_policies",
            ["location_id"],
            unique=False,
        )
    if not _has_index("inventory_cycle_counts", "idx_inventory_cycle_counts_org"):
        op.create_index(
            "idx_inventory_cycle_counts_org",
            "inventory_cycle_counts",
            ["organization_id"],
            unique=False,
        )
    if not _has_index("inventory_cycle_counts", "idx_inventory_cycle_counts_item"):
        op.create_index(
            "idx_inventory_cycle_counts_item",
            "inventory_cycle_counts",
            ["stock_item_id"],
            unique=False,
        )
    if not _has_index("inventory_cycle_counts", "idx_inventory_cycle_counts_storeroom"):
        op.create_index(
            "idx_inventory_cycle_counts_storeroom",
            "inventory_cycle_counts",
            ["storeroom_id"],
            unique=False,
        )
    if not _has_index("inventory_cycle_counts", "idx_inventory_cycle_counts_location"):
        op.create_index(
            "idx_inventory_cycle_counts_location",
            "inventory_cycle_counts",
            ["location_id"],
            unique=False,
        )
    if not _has_index("inventory_cycle_counts", "idx_inventory_cycle_counts_status"):
        op.create_index(
            "idx_inventory_cycle_counts_status",
            "inventory_cycle_counts",
            ["status"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("inventory_cycle_counts", "idx_inventory_cycle_counts_status"):
        op.drop_index("idx_inventory_cycle_counts_status", table_name="inventory_cycle_counts")
    if _has_index("inventory_cycle_counts", "idx_inventory_cycle_counts_location"):
        op.drop_index("idx_inventory_cycle_counts_location", table_name="inventory_cycle_counts")
    if _has_index("inventory_cycle_counts", "idx_inventory_cycle_counts_storeroom"):
        op.drop_index("idx_inventory_cycle_counts_storeroom", table_name="inventory_cycle_counts")
    if _has_index("inventory_cycle_counts", "idx_inventory_cycle_counts_item"):
        op.drop_index("idx_inventory_cycle_counts_item", table_name="inventory_cycle_counts")
    if _has_index("inventory_cycle_counts", "idx_inventory_cycle_counts_org"):
        op.drop_index("idx_inventory_cycle_counts_org", table_name="inventory_cycle_counts")
    if _has_index("inventory_reorder_policies", "idx_inventory_reorder_policies_location"):
        op.drop_index("idx_inventory_reorder_policies_location", table_name="inventory_reorder_policies")
    if _has_index("inventory_reorder_policies", "idx_inventory_reorder_policies_storeroom"):
        op.drop_index("idx_inventory_reorder_policies_storeroom", table_name="inventory_reorder_policies")
    if _has_index("inventory_reorder_policies", "idx_inventory_reorder_policies_item"):
        op.drop_index("idx_inventory_reorder_policies_item", table_name="inventory_reorder_policies")
    if _has_index("inventory_reorder_policies", "idx_inventory_reorder_policies_org"):
        op.drop_index("idx_inventory_reorder_policies_org", table_name="inventory_reorder_policies")
    if _has_index("inventory_storage_locations", "idx_inventory_storage_locations_active"):
        op.drop_index("idx_inventory_storage_locations_active", table_name="inventory_storage_locations")
    if _has_index("inventory_storage_locations", "idx_inventory_storage_locations_parent"):
        op.drop_index("idx_inventory_storage_locations_parent", table_name="inventory_storage_locations")
    if _has_index("inventory_storage_locations", "idx_inventory_storage_locations_storeroom"):
        op.drop_index("idx_inventory_storage_locations_storeroom", table_name="inventory_storage_locations")
    if _has_index("inventory_storage_locations", "idx_inventory_storage_locations_org"):
        op.drop_index("idx_inventory_storage_locations_org", table_name="inventory_storage_locations")
    if _has_table("inventory_cycle_counts"):
        op.drop_table("inventory_cycle_counts")
    if _has_table("inventory_reorder_policies"):
        op.drop_table("inventory_reorder_policies")
    if _has_table("inventory_storage_locations"):
        op.drop_table("inventory_storage_locations")
