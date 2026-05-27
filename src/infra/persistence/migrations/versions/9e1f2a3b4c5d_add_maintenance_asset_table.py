"""add maintenance asset table

Revision ID: 9e1f2a3b4c5d
Revises: 8d9e1f2a3b4c
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa


revision = "9e1f2a3b4c5d"
down_revision = "8d9e1f2a3b4c"
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
    if not _has_table("maintenance_assets"):
        op.create_table(
            "maintenance_assets",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("site_id", sa.String(), nullable=False),
            sa.Column("location_id", sa.String(), nullable=False),
            sa.Column("asset_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("system_id", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("parent_asset_id", sa.String(), nullable=True),
            sa.Column("asset_type", sa.String(length=64), nullable=True),
            sa.Column("asset_category", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=8), nullable=False, server_default="ACTIVE"),
            sa.Column("criticality", sa.String(length=8), nullable=False, server_default="MEDIUM"),
            sa.Column("manufacturer_party_id", sa.String(), nullable=True),
            sa.Column("supplier_party_id", sa.String(), nullable=True),
            sa.Column("model_number", sa.String(length=128), nullable=True),
            sa.Column("serial_number", sa.String(length=128), nullable=True),
            sa.Column("barcode", sa.String(length=128), nullable=True),
            sa.Column("install_date", sa.Date(), nullable=True),
            sa.Column("commission_date", sa.Date(), nullable=True),
            sa.Column("warranty_start", sa.Date(), nullable=True),
            sa.Column("warranty_end", sa.Date(), nullable=True),
            sa.Column("expected_life_years", sa.Integer(), nullable=True),
            sa.Column("replacement_cost", sa.Numeric(18, 2), nullable=True),
            sa.Column("maintenance_strategy", sa.String(length=128), nullable=True),
            sa.Column("service_level", sa.String(length=128), nullable=True),
            sa.Column("requires_shutdown_for_major_work", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_assets_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["site_id"],
                ["sites.id"],
                name="fk_maintenance_assets_site_id",
            ),
            sa.ForeignKeyConstraint(
                ["location_id"],
                ["maintenance_locations.id"],
                name="fk_maintenance_assets_location_id",
            ),
            sa.ForeignKeyConstraint(
                ["system_id"],
                ["maintenance_systems.id"],
                name="fk_maintenance_assets_system_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["parent_asset_id"],
                ["maintenance_assets.id"],
                name="fk_maintenance_assets_parent_asset_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["manufacturer_party_id"],
                ["parties.id"],
                name="fk_maintenance_assets_manufacturer_party_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["supplier_party_id"],
                ["parties.id"],
                name="fk_maintenance_assets_supplier_party_id",
                ondelete="SET NULL",
            ),
            sa.UniqueConstraint("organization_id", "asset_code", name="ux_maintenance_assets_org_code"),
        )

    for index_name, columns in (
        ("idx_maintenance_assets_org", ["organization_id"]),
        ("idx_maintenance_assets_site", ["site_id"]),
        ("idx_maintenance_assets_location", ["location_id"]),
        ("idx_maintenance_assets_system", ["system_id"]),
        ("idx_maintenance_assets_parent", ["parent_asset_id"]),
        ("idx_maintenance_assets_manufacturer", ["manufacturer_party_id"]),
        ("idx_maintenance_assets_supplier", ["supplier_party_id"]),
        ("idx_maintenance_assets_active", ["is_active"]),
    ):
        if not _has_index("maintenance_assets", index_name):
            op.create_index(index_name, "maintenance_assets", columns, unique=False)


def downgrade() -> None:
    if _has_table("maintenance_assets"):
        for index_name in (
            "idx_maintenance_assets_active",
            "idx_maintenance_assets_supplier",
            "idx_maintenance_assets_manufacturer",
            "idx_maintenance_assets_parent",
            "idx_maintenance_assets_system",
            "idx_maintenance_assets_location",
            "idx_maintenance_assets_site",
            "idx_maintenance_assets_org",
        ):
            if _has_index("maintenance_assets", index_name):
                op.drop_index(index_name, table_name="maintenance_assets")
        op.drop_table("maintenance_assets")
