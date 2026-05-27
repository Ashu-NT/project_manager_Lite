"""add maintenance material requirement table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
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
    if not _has_table("maintenance_work_order_material_requirements"):
        op.create_table(
            "maintenance_work_order_material_requirements",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("work_order_id", sa.String(), nullable=False),
            sa.Column("stock_item_id", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("required_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("issued_qty", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("required_uom", sa.String(length=32), nullable=False, server_default=""),
            sa.Column("is_stock_item", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("preferred_storeroom_id", sa.String(), nullable=True),
            sa.Column("procurement_status", sa.String(length=24), nullable=False, server_default="PLANNED"),
            sa.Column("last_availability_status", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("last_missing_qty", sa.Numeric(18, 6), nullable=True),
            sa.Column("linked_requisition_id", sa.String(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_material_requirements_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["work_order_id"],
                ["maintenance_work_orders.id"],
                name="fk_maintenance_material_requirements_work_order_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["stock_item_id"],
                ["inventory_stock_items.id"],
                name="fk_maintenance_material_requirements_stock_item_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["preferred_storeroom_id"],
                ["inventory_storerooms.id"],
                name="fk_maintenance_material_requirements_storeroom_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["linked_requisition_id"],
                ["inventory_purchase_requisitions.id"],
                name="fk_maintenance_material_requirements_requisition_id",
                ondelete="SET NULL",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_material_requirements_org", ["organization_id"]),
        ("idx_maintenance_material_requirements_work_order", ["work_order_id"]),
        ("idx_maintenance_material_requirements_stock_item", ["stock_item_id"]),
        ("idx_maintenance_material_requirements_storeroom", ["preferred_storeroom_id"]),
        ("idx_maintenance_material_requirements_status", ["procurement_status"]),
        ("idx_maintenance_material_requirements_requisition", ["linked_requisition_id"]),
    ):
        if not _has_index("maintenance_work_order_material_requirements", index_name):
            op.create_index(index_name, "maintenance_work_order_material_requirements", columns, unique=False)


def downgrade() -> None:
    if _has_table("maintenance_work_order_material_requirements"):
        for index_name in (
            "idx_maintenance_material_requirements_requisition",
            "idx_maintenance_material_requirements_status",
            "idx_maintenance_material_requirements_storeroom",
            "idx_maintenance_material_requirements_stock_item",
            "idx_maintenance_material_requirements_work_order",
            "idx_maintenance_material_requirements_org",
        ):
            if _has_index("maintenance_work_order_material_requirements", index_name):
                op.drop_index(index_name, table_name="maintenance_work_order_material_requirements")
        op.drop_table("maintenance_work_order_material_requirements")
