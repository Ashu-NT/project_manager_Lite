"""add preventive schedule policy and instances

Revision ID: f0a1b2c3d4e5
Revises: e1f2a3b4c5d6
Create Date: 2026-04-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f0a1b2c3d4e5"
down_revision = "e1f2a3b4c5d6"
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


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def upgrade() -> None:
    with op.batch_alter_table("maintenance_preventive_plans") as batch:
        if not _has_column("maintenance_preventive_plans", "schedule_policy"):
            batch.add_column(
                sa.Column(
                    "schedule_policy",
                    sa.String(length=16),
                    nullable=False,
                    server_default="FIXED",
                )
            )
        if not _has_column("maintenance_preventive_plans", "generation_horizon_count"):
            batch.add_column(
                sa.Column(
                    "generation_horizon_count",
                    sa.Integer(),
                    nullable=False,
                    server_default="13",
                )
            )

    if not _has_table("maintenance_preventive_plan_instances"):
        op.create_table(
            "maintenance_preventive_plan_instances",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("plan_id", sa.String(), nullable=False),
            sa.Column("due_at", sa.DateTime(), nullable=False),
            sa.Column("due_counter", sa.Numeric(18, 6), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="PLANNED"),
            sa.Column("generated_at", sa.DateTime(), nullable=True),
            sa.Column("generated_work_request_id", sa.String(), nullable=True),
            sa.Column("generated_work_order_id", sa.String(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "plan_id",
                "due_at",
                name="ux_maintenance_preventive_plan_instances_plan_due_at",
            ),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_preventive_instances_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["plan_id"],
                ["maintenance_preventive_plans.id"],
                name="fk_maintenance_preventive_instances_plan_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["generated_work_request_id"],
                ["maintenance_work_requests.id"],
                name="fk_maintenance_preventive_instances_work_request_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["generated_work_order_id"],
                ["maintenance_work_orders.id"],
                name="fk_maintenance_preventive_instances_work_order_id",
                ondelete="SET NULL",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_preventive_instances_org", ["organization_id"]),
        ("idx_maintenance_preventive_instances_plan", ["plan_id"]),
        ("idx_maintenance_preventive_instances_due_at", ["due_at"]),
        ("idx_maintenance_preventive_instances_status", ["status"]),
        ("idx_maintenance_preventive_instances_work_request", ["generated_work_request_id"]),
        ("idx_maintenance_preventive_instances_work_order", ["generated_work_order_id"]),
    ):
        if not _has_index("maintenance_preventive_plan_instances", index_name):
            op.create_index(index_name, "maintenance_preventive_plan_instances", columns, unique=False)


def downgrade() -> None:
    for index_name in (
        "idx_maintenance_preventive_instances_work_order",
        "idx_maintenance_preventive_instances_work_request",
        "idx_maintenance_preventive_instances_status",
        "idx_maintenance_preventive_instances_due_at",
        "idx_maintenance_preventive_instances_plan",
        "idx_maintenance_preventive_instances_org",
    ):
        if _has_index("maintenance_preventive_plan_instances", index_name):
            op.drop_index(index_name, table_name="maintenance_preventive_plan_instances")
    if _has_table("maintenance_preventive_plan_instances"):
        op.drop_table("maintenance_preventive_plan_instances")
    with op.batch_alter_table("maintenance_preventive_plans") as batch:
        if _has_column("maintenance_preventive_plans", "generation_horizon_count"):
            batch.drop_column("generation_horizon_count")
        if _has_column("maintenance_preventive_plans", "schedule_policy"):
            batch.drop_column("schedule_policy")
