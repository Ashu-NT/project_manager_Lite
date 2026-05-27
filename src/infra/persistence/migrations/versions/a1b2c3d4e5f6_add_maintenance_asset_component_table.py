"""add maintenance asset component table

Revision ID: a1b2c3d4e5f6
Revises: 9e1f2a3b4c5d
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "9e1f2a3b4c5d"
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
    if not _has_table("maintenance_asset_components"):
        op.create_table(
            "maintenance_asset_components",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("asset_id", sa.String(), nullable=False),
            sa.Column("component_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("parent_component_id", sa.String(), nullable=True),
            sa.Column("component_type", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=8), nullable=False, server_default="ACTIVE"),
            sa.Column("manufacturer_party_id", sa.String(), nullable=True),
            sa.Column("supplier_party_id", sa.String(), nullable=True),
            sa.Column("manufacturer_part_number", sa.String(length=128), nullable=True),
            sa.Column("supplier_part_number", sa.String(length=128), nullable=True),
            sa.Column("model_number", sa.String(length=128), nullable=True),
            sa.Column("serial_number", sa.String(length=128), nullable=True),
            sa.Column("install_date", sa.Date(), nullable=True),
            sa.Column("warranty_end", sa.Date(), nullable=True),
            sa.Column("expected_life_hours", sa.Integer(), nullable=True),
            sa.Column("expected_life_cycles", sa.Integer(), nullable=True),
            sa.Column("is_critical_component", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_components_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["asset_id"],
                ["maintenance_assets.id"],
                name="fk_maintenance_components_asset_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["parent_component_id"],
                ["maintenance_asset_components.id"],
                name="fk_maintenance_components_parent_component_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["manufacturer_party_id"],
                ["parties.id"],
                name="fk_maintenance_components_manufacturer_party_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["supplier_party_id"],
                ["parties.id"],
                name="fk_maintenance_components_supplier_party_id",
                ondelete="SET NULL",
            ),
            sa.UniqueConstraint("organization_id", "component_code", name="ux_maintenance_components_org_code"),
        )

    for index_name, columns in (
        ("idx_maintenance_components_org", ["organization_id"]),
        ("idx_maintenance_components_asset", ["asset_id"]),
        ("idx_maintenance_components_parent", ["parent_component_id"]),
        ("idx_maintenance_components_manufacturer", ["manufacturer_party_id"]),
        ("idx_maintenance_components_supplier", ["supplier_party_id"]),
        ("idx_maintenance_components_active", ["is_active"]),
    ):
        if not _has_index("maintenance_asset_components", index_name):
            op.create_index(index_name, "maintenance_asset_components", columns, unique=False)


def downgrade() -> None:
    if _has_table("maintenance_asset_components"):
        for index_name in (
            "idx_maintenance_components_active",
            "idx_maintenance_components_supplier",
            "idx_maintenance_components_manufacturer",
            "idx_maintenance_components_parent",
            "idx_maintenance_components_asset",
            "idx_maintenance_components_org",
        ):
            if _has_index("maintenance_asset_components", index_name):
                op.drop_index(index_name, table_name="maintenance_asset_components")
        op.drop_table("maintenance_asset_components")
