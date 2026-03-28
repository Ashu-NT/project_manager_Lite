"""add inventory item category master

Revision ID: 3c5d7e9f1a2b
Revises: 2d4e6f8a9b0c
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa


revision = "3c5d7e9f1a2b"
down_revision = "2d4e6f8a9b0c"
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
    if not _has_table("inventory_item_categories"):
        op.create_table(
            "inventory_item_categories",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("category_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "category_type",
                sa.String(length=32),
                nullable=False,
                server_default="MATERIAL",
            ),
            sa.Column(
                "is_equipment",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "supports_project_usage",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "supports_maintenance_usage",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            ),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "category_code", name="ux_inventory_item_categories_org_code"),
        )
    if not _has_index("inventory_item_categories", "idx_inventory_item_categories_org"):
        op.create_index(
            "idx_inventory_item_categories_org",
            "inventory_item_categories",
            ["organization_id"],
        )
    if not _has_index("inventory_item_categories", "idx_inventory_item_categories_active"):
        op.create_index(
            "idx_inventory_item_categories_active",
            "inventory_item_categories",
            ["is_active"],
        )


def downgrade() -> None:
    if _has_index("inventory_item_categories", "idx_inventory_item_categories_active"):
        op.drop_index("idx_inventory_item_categories_active", table_name="inventory_item_categories")
    if _has_index("inventory_item_categories", "idx_inventory_item_categories_org"):
        op.drop_index("idx_inventory_item_categories_org", table_name="inventory_item_categories")
    if _has_table("inventory_item_categories"):
        op.drop_table("inventory_item_categories")
