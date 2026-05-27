"""add maintenance reliability tables

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-04-03 12:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maintenance_failure_codes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "code_type",
            sa.Enum("SYMPTOM", "CAUSE", "REMEDY", name="maintenancefailurecodetype"),
            nullable=False,
            server_default="SYMPTOM",
        ),
        sa.Column("parent_code_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_code_id"], ["maintenance_failure_codes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "failure_code", name="ux_maintenance_failure_codes_org_code"),
    )

    op.create_table(
        "maintenance_downtime_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=True),
        sa.Column("system_id", sa.String(), nullable=True),
        sa.Column("work_order_id", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("downtime_type", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("impact_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["maintenance_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["system_id"], ["maintenance_systems.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["work_order_id"], ["maintenance_work_orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maintenance_downtime_events_work_order",
        "maintenance_downtime_events",
        ["work_order_id"],
    )
    op.create_index(
        "ix_maintenance_downtime_events_asset",
        "maintenance_downtime_events",
        ["asset_id"],
    )
    op.create_index(
        "ix_maintenance_downtime_events_system",
        "maintenance_downtime_events",
        ["system_id"],
    )
    op.create_index(
        "ix_maintenance_downtime_events_start",
        "maintenance_downtime_events",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_maintenance_downtime_events_start", table_name="maintenance_downtime_events")
    op.drop_index("ix_maintenance_downtime_events_system", table_name="maintenance_downtime_events")
    op.drop_index("ix_maintenance_downtime_events_asset", table_name="maintenance_downtime_events")
    op.drop_index("ix_maintenance_downtime_events_work_order", table_name="maintenance_downtime_events")
    op.drop_table("maintenance_downtime_events")
    op.drop_table("maintenance_failure_codes")
