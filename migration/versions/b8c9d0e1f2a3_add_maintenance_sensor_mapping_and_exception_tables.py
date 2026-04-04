"""add maintenance sensor mapping and exception tables

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa


revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
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
    if not _has_table("maintenance_sensor_source_mappings"):
        op.create_table(
            "maintenance_sensor_source_mappings",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("integration_source_id", sa.String(), nullable=False),
            sa.Column("sensor_id", sa.String(), nullable=False),
            sa.Column("external_equipment_key", sa.String(length=128), nullable=True),
            sa.Column("external_measurement_key", sa.String(length=128), nullable=False),
            sa.Column("transform_rule", sa.Text(), nullable=True),
            sa.Column("unit_conversion_rule", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "integration_source_id",
                "sensor_id",
                "external_equipment_key",
                "external_measurement_key",
                name="ux_maintenance_sensor_source_mappings_unique",
            ),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_sensor_source_mappings_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["integration_source_id"],
                ["maintenance_integration_sources.id"],
                name="fk_maintenance_sensor_source_mappings_integration_source_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["sensor_id"],
                ["maintenance_sensors.id"],
                name="fk_maintenance_sensor_source_mappings_sensor_id",
                ondelete="CASCADE",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_sensor_source_mappings_org", ["organization_id"]),
        ("idx_maintenance_sensor_source_mappings_source", ["integration_source_id"]),
        ("idx_maintenance_sensor_source_mappings_sensor", ["sensor_id"]),
    ):
        if not _has_index("maintenance_sensor_source_mappings", index_name):
            op.create_index(index_name, "maintenance_sensor_source_mappings", columns, unique=False)

    if not _has_table("maintenance_sensor_exceptions"):
        op.create_table(
            "maintenance_sensor_exceptions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("sensor_id", sa.String(), nullable=True),
            sa.Column("integration_source_id", sa.String(), nullable=True),
            sa.Column("source_mapping_id", sa.String(), nullable=True),
            sa.Column("exception_type", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="OPEN"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("source_batch_id", sa.String(length=128), nullable=True),
            sa.Column("raw_payload_ref", sa.String(length=256), nullable=True),
            sa.Column("detected_at", sa.DateTime(), nullable=False),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
            sa.Column("acknowledged_by_user_id", sa.String(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by_user_id", sa.String(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_sensor_exceptions_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["sensor_id"],
                ["maintenance_sensors.id"],
                name="fk_maintenance_sensor_exceptions_sensor_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["integration_source_id"],
                ["maintenance_integration_sources.id"],
                name="fk_maintenance_sensor_exceptions_integration_source_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["source_mapping_id"],
                ["maintenance_sensor_source_mappings.id"],
                name="fk_maintenance_sensor_exceptions_source_mapping_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["acknowledged_by_user_id"],
                ["users.id"],
                name="fk_maintenance_sensor_exceptions_ack_user_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["resolved_by_user_id"],
                ["users.id"],
                name="fk_maintenance_sensor_exceptions_resolve_user_id",
                ondelete="SET NULL",
            ),
        )

    for index_name, columns in (
        ("ix_maintenance_sensor_exceptions_status", ["status"]),
        ("ix_maintenance_sensor_exceptions_sensor", ["sensor_id"]),
        ("ix_maintenance_sensor_exceptions_integration_source", ["integration_source_id"]),
    ):
        if not _has_index("maintenance_sensor_exceptions", index_name):
            op.create_index(index_name, "maintenance_sensor_exceptions", columns, unique=False)


def downgrade() -> None:
    if _has_table("maintenance_sensor_exceptions"):
        for index_name in (
            "ix_maintenance_sensor_exceptions_integration_source",
            "ix_maintenance_sensor_exceptions_sensor",
            "ix_maintenance_sensor_exceptions_status",
        ):
            if _has_index("maintenance_sensor_exceptions", index_name):
                op.drop_index(index_name, table_name="maintenance_sensor_exceptions")
        op.drop_table("maintenance_sensor_exceptions")

    if _has_table("maintenance_sensor_source_mappings"):
        for index_name in (
            "idx_maintenance_sensor_source_mappings_sensor",
            "idx_maintenance_sensor_source_mappings_source",
            "idx_maintenance_sensor_source_mappings_org",
        ):
            if _has_index("maintenance_sensor_source_mappings", index_name):
                op.drop_index(index_name, table_name="maintenance_sensor_source_mappings")
        op.drop_table("maintenance_sensor_source_mappings")
