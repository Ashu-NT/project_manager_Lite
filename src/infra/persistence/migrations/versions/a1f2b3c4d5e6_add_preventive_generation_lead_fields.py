"""add preventive generation lead fields

Revision ID: a1f2b3c4d5e6
Revises: f0a1b2c3d4e5
Create Date: 2026-04-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a1f2b3c4d5e6"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def upgrade() -> None:
    with op.batch_alter_table("maintenance_preventive_plans") as batch:
        if not _has_column("maintenance_preventive_plans", "generation_lead_value"):
            batch.add_column(
                sa.Column(
                    "generation_lead_value",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
            )
        if not _has_column("maintenance_preventive_plans", "generation_lead_unit"):
            batch.add_column(
                sa.Column(
                    "generation_lead_unit",
                    sa.String(length=16),
                    nullable=False,
                    server_default="DAYS",
                )
            )


def downgrade() -> None:
    if not _has_table("maintenance_preventive_plans"):
        return
    with op.batch_alter_table("maintenance_preventive_plans") as batch:
        if _has_column("maintenance_preventive_plans", "generation_lead_unit"):
            batch.drop_column("generation_lead_unit")
        if _has_column("maintenance_preventive_plans", "generation_lead_value"):
            batch.drop_column("generation_lead_value")
