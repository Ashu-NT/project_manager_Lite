"""add maintenance sensor and reading tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
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
    if not _has_table("maintenance_sensors"):
        op.create_table(
            "maintenance_sensors",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("site_id", sa.String(), nullable=False),
            sa.Column("sensor_code", sa.String(length=64), nullable=False),
            sa.Column("sensor_name", sa.String(length=256), nullable=False),
            sa.Column("sensor_tag", sa.String(length=128), nullable=True),
            sa.Column("sensor_type", sa.String(length=64), nullable=True),
            sa.Column("asset_id", sa.String(), nullable=True),
            sa.Column("component_id", sa.String(), nullable=True),
            sa.Column("system_id", sa.String(), nullable=True),
            sa.Column("source_type", sa.String(length=64), nullable=True),
            sa.Column("source_name", sa.String(length=128), nullable=True),
            sa.Column("source_key", sa.String(length=128), nullable=True),
            sa.Column("unit", sa.String(length=32), nullable=True),
            sa.Column("current_value", sa.Numeric(18, 6), nullable=True),
            sa.Column("last_read_at", sa.DateTime(), nullable=True),
            sa.Column("last_quality_state", sa.String(length=16), nullable=False, server_default="VALID"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "sensor_code", name="ux_maintenance_sensors_org_code"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_sensors_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["site_id"],
                ["sites.id"],
                name="fk_maintenance_sensors_site_id",
            ),
            sa.ForeignKeyConstraint(
                ["asset_id"],
                ["maintenance_assets.id"],
                name="fk_maintenance_sensors_asset_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["component_id"],
                ["maintenance_asset_components.id"],
                name="fk_maintenance_sensors_component_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["system_id"],
                ["maintenance_systems.id"],
                name="fk_maintenance_sensors_system_id",
                ondelete="SET NULL",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_sensors_org", ["organization_id"]),
        ("idx_maintenance_sensors_site", ["site_id"]),
        ("idx_maintenance_sensors_asset", ["asset_id"]),
        ("idx_maintenance_sensors_component", ["component_id"]),
        ("idx_maintenance_sensors_system", ["system_id"]),
        ("idx_maintenance_sensors_type", ["sensor_type"]),
    ):
        if not _has_index("maintenance_sensors", index_name):
            op.create_index(index_name, "maintenance_sensors", columns, unique=False)

    if not _has_table("maintenance_sensor_readings"):
        op.create_table(
            "maintenance_sensor_readings",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("sensor_id", sa.String(), nullable=False),
            sa.Column("reading_value", sa.Numeric(18, 6), nullable=False),
            sa.Column("reading_unit", sa.String(length=32), nullable=False),
            sa.Column("reading_timestamp", sa.DateTime(), nullable=False),
            sa.Column("quality_state", sa.String(length=16), nullable=False, server_default="VALID"),
            sa.Column("source_name", sa.String(length=128), nullable=True),
            sa.Column("source_batch_id", sa.String(length=128), nullable=True),
            sa.Column("received_at", sa.DateTime(), nullable=True),
            sa.Column("raw_payload_ref", sa.String(length=256), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_sensor_readings_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["sensor_id"],
                ["maintenance_sensors.id"],
                name="fk_maintenance_sensor_readings_sensor_id",
                ondelete="CASCADE",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_sensor_readings_sensor_timestamp", ["sensor_id", "reading_timestamp"]),
        ("idx_maintenance_sensor_readings_org_batch", ["organization_id", "source_batch_id"]),
        ("idx_maintenance_sensor_readings_quality", ["quality_state"]),
    ):
        if not _has_index("maintenance_sensor_readings", index_name):
            op.create_index(index_name, "maintenance_sensor_readings", columns, unique=False)


def downgrade() -> None:
    if _has_table("maintenance_sensor_readings"):
        for index_name in (
            "idx_maintenance_sensor_readings_quality",
            "idx_maintenance_sensor_readings_org_batch",
            "idx_maintenance_sensor_readings_sensor_timestamp",
        ):
            if _has_index("maintenance_sensor_readings", index_name):
                op.drop_index(index_name, table_name="maintenance_sensor_readings")
        op.drop_table("maintenance_sensor_readings")

    if _has_table("maintenance_sensors"):
        for index_name in (
            "idx_maintenance_sensors_type",
            "idx_maintenance_sensors_system",
            "idx_maintenance_sensors_component",
            "idx_maintenance_sensors_asset",
            "idx_maintenance_sensors_site",
            "idx_maintenance_sensors_org",
        ):
            if _has_index("maintenance_sensors", index_name):
                op.drop_index(index_name, table_name="maintenance_sensors")
        op.drop_table("maintenance_sensors")
