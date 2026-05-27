"""add maintenance work order task table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
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
    if not _has_table("maintenance_work_order_tasks"):
        op.create_table(
            "maintenance_work_order_tasks",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("work_order_id", sa.String(), nullable=False),
            sa.Column("task_template_id", sa.String(), nullable=True),
            sa.Column("task_name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("assigned_employee_id", sa.String(), nullable=True),
            sa.Column("assigned_team_id", sa.String(), nullable=True),
            sa.Column("estimated_minutes", sa.Integer(), nullable=True),
            sa.Column("actual_minutes", sa.Integer(), nullable=True),
            sa.Column("required_skill", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="NOT_STARTED"),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("sequence_no", sa.Integer(), nullable=False),
            sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("completion_rule", sa.String(length=20), nullable=False, server_default="NO_STEPS_REQUIRED"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_work_order_tasks_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["work_order_id"],
                ["maintenance_work_orders.id"],
                name="fk_maintenance_work_order_tasks_work_order_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["assigned_employee_id"],
                ["employees.id"],
                name="fk_maintenance_work_order_tasks_assigned_employee_id",
                ondelete="SET NULL",
            ),
            sa.UniqueConstraint(
                "organization_id",
                "work_order_id",
                "sequence_no",
                name="ux_maintenance_work_order_tasks_work_order_sequence",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_work_order_tasks_org", ["organization_id"]),
        ("idx_maintenance_work_order_tasks_work_order", ["work_order_id"]),
        ("idx_maintenance_work_order_tasks_status", ["status"]),
        ("idx_maintenance_work_order_tasks_assigned_employee", ["assigned_employee_id"]),
        ("idx_maintenance_work_order_tasks_assigned_team", ["assigned_team_id"]),
    ):
        if not _has_index("maintenance_work_order_tasks", index_name):
            op.create_index(index_name, "maintenance_work_order_tasks", columns, unique=False)


def downgrade() -> None:
    if _has_table("maintenance_work_order_tasks"):
        for index_name in (
            "idx_maintenance_work_order_tasks_assigned_team",
            "idx_maintenance_work_order_tasks_assigned_employee",
            "idx_maintenance_work_order_tasks_status",
            "idx_maintenance_work_order_tasks_work_order",
            "idx_maintenance_work_order_tasks_org",
        ):
            if _has_index("maintenance_work_order_tasks", index_name):
                op.drop_index(index_name, table_name="maintenance_work_order_tasks")
        op.drop_table("maintenance_work_order_tasks")
