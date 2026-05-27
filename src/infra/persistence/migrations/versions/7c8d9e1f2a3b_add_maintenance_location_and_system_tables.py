"""add maintenance location and system tables

Revision ID: 7c8d9e1f2a3b
Revises: 6b7c8d9e1f2a
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa


revision = "7c8d9e1f2a3b"
down_revision = "6b7c8d9e1f2a"
branch_labels = None
depends_on = None

_MAINTENANCE_CRITICALITY_ENUM = sa.Enum(
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
    name="maintenancecriticality",
)
_MAINTENANCE_STATUS_ENUM = sa.Enum(
    "DRAFT",
    "ACTIVE",
    "INACTIVE",
    "RETIRED",
    name="maintenancelifecyclestatus",
)


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def upgrade() -> None:
    if not _has_table("maintenance_locations"):
        op.create_table(
            "maintenance_locations",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("site_id", sa.String(), nullable=False),
            sa.Column("location_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("parent_location_id", sa.String(), nullable=True),
            sa.Column("location_type", sa.String(length=64), nullable=True),
            sa.Column("criticality", _MAINTENANCE_CRITICALITY_ENUM, nullable=False, server_default="MEDIUM"),
            sa.Column("status", _MAINTENANCE_STATUS_ENUM, nullable=False, server_default="ACTIVE"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["parent_location_id"], ["maintenance_locations.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "location_code", name="ux_maintenance_locations_org_code"),
        )

    if not _has_table("maintenance_systems"):
        op.create_table(
            "maintenance_systems",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("site_id", sa.String(), nullable=False),
            sa.Column("system_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("location_id", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("parent_system_id", sa.String(), nullable=True),
            sa.Column("system_type", sa.String(length=64), nullable=True),
            sa.Column("criticality", _MAINTENANCE_CRITICALITY_ENUM, nullable=False, server_default="MEDIUM"),
            sa.Column("status", _MAINTENANCE_STATUS_ENUM, nullable=False, server_default="ACTIVE"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["location_id"], ["maintenance_locations.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["parent_system_id"], ["maintenance_systems.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "system_code", name="ux_maintenance_systems_org_code"),
        )

    index_specs = (
        ("maintenance_locations", "idx_maintenance_locations_org", ["organization_id"]),
        ("maintenance_locations", "idx_maintenance_locations_site", ["site_id"]),
        ("maintenance_locations", "idx_maintenance_locations_parent", ["parent_location_id"]),
        ("maintenance_locations", "idx_maintenance_locations_active", ["is_active"]),
        ("maintenance_systems", "idx_maintenance_systems_org", ["organization_id"]),
        ("maintenance_systems", "idx_maintenance_systems_site", ["site_id"]),
        ("maintenance_systems", "idx_maintenance_systems_location", ["location_id"]),
        ("maintenance_systems", "idx_maintenance_systems_parent", ["parent_system_id"]),
        ("maintenance_systems", "idx_maintenance_systems_active", ["is_active"]),
    )
    for table_name, index_name, columns in index_specs:
        if _has_table(table_name) and not _has_index(table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    index_specs = (
        ("maintenance_systems", "idx_maintenance_systems_active"),
        ("maintenance_systems", "idx_maintenance_systems_parent"),
        ("maintenance_systems", "idx_maintenance_systems_location"),
        ("maintenance_systems", "idx_maintenance_systems_site"),
        ("maintenance_systems", "idx_maintenance_systems_org"),
        ("maintenance_locations", "idx_maintenance_locations_active"),
        ("maintenance_locations", "idx_maintenance_locations_parent"),
        ("maintenance_locations", "idx_maintenance_locations_site"),
        ("maintenance_locations", "idx_maintenance_locations_org"),
    )
    for table_name, index_name in index_specs:
        if _has_index(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)

    if _has_table("maintenance_systems"):
        op.drop_table("maintenance_systems")
    if _has_table("maintenance_locations"):
        op.drop_table("maintenance_locations")
