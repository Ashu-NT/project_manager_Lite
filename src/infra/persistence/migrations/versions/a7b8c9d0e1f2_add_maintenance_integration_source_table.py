"""add maintenance integration source table

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
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
    if not _has_table("maintenance_integration_sources"):
        op.create_table(
            "maintenance_integration_sources",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("integration_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("integration_type", sa.String(length=64), nullable=False),
            sa.Column("endpoint_or_path", sa.String(length=512), nullable=True),
            sa.Column("authentication_mode", sa.String(length=64), nullable=True),
            sa.Column("schedule_expression", sa.String(length=128), nullable=True),
            sa.Column("last_successful_sync_at", sa.DateTime(), nullable=True),
            sa.Column("last_failed_sync_at", sa.DateTime(), nullable=True),
            sa.Column("last_error_message", sa.Text(), nullable=False, server_default=""),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "integration_code",
                name="ux_maintenance_integration_sources_org_code",
            ),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_integration_sources_organization_id",
                ondelete="CASCADE",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_integration_sources_org", ["organization_id"]),
        ("idx_maintenance_integration_sources_type", ["integration_type"]),
        ("idx_maintenance_integration_sources_active", ["is_active"]),
    ):
        if not _has_index("maintenance_integration_sources", index_name):
            op.create_index(index_name, "maintenance_integration_sources", columns, unique=False)


def downgrade() -> None:
    if _has_table("maintenance_integration_sources"):
        for index_name in (
            "idx_maintenance_integration_sources_active",
            "idx_maintenance_integration_sources_type",
            "idx_maintenance_integration_sources_org",
        ):
            if _has_index("maintenance_integration_sources", index_name):
                op.drop_index(index_name, table_name="maintenance_integration_sources")
        op.drop_table("maintenance_integration_sources")
