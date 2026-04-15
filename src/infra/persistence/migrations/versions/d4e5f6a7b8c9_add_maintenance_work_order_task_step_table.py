"""add maintenance work order task step table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
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
    if not _has_table("maintenance_work_order_task_steps"):
        op.create_table(
            "maintenance_work_order_task_steps",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("work_order_task_id", sa.String(), nullable=False),
            sa.Column("source_step_template_id", sa.String(), nullable=True),
            sa.Column("step_number", sa.Integer(), nullable=False),
            sa.Column("instruction", sa.Text(), nullable=False),
            sa.Column("expected_result", sa.Text(), nullable=False, server_default=""),
            sa.Column("hint_level", sa.String(length=32), nullable=False, server_default=""),
            sa.Column("hint_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="NOT_STARTED"),
            sa.Column("requires_confirmation", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("requires_measurement", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("requires_photo", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("measurement_value", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("measurement_unit", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("completed_by_user_id", sa.String(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("confirmed_by_user_id", sa.String(), nullable=True),
            sa.Column("confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_maintenance_work_order_task_steps_organization_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["work_order_task_id"],
                ["maintenance_work_order_tasks.id"],
                name="fk_maintenance_work_order_task_steps_work_order_task_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["completed_by_user_id"],
                ["users.id"],
                name="fk_maintenance_work_order_task_steps_completed_by_user_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["confirmed_by_user_id"],
                ["users.id"],
                name="fk_maintenance_work_order_task_steps_confirmed_by_user_id",
                ondelete="SET NULL",
            ),
            sa.UniqueConstraint(
                "organization_id",
                "work_order_task_id",
                "step_number",
                name="ux_maintenance_work_order_task_steps_task_step_number",
            ),
        )

    for index_name, columns in (
        ("idx_maintenance_work_order_task_steps_org", ["organization_id"]),
        ("idx_maintenance_work_order_task_steps_task", ["work_order_task_id"]),
        ("idx_maintenance_work_order_task_steps_status", ["status"]),
        ("idx_maintenance_work_order_task_steps_completed_by", ["completed_by_user_id"]),
        ("idx_maintenance_work_order_task_steps_confirmed_by", ["confirmed_by_user_id"]),
    ):
        if not _has_index("maintenance_work_order_task_steps", index_name):
            op.create_index(index_name, "maintenance_work_order_task_steps", columns, unique=False)


def downgrade() -> None:
    if _has_table("maintenance_work_order_task_steps"):
        for index_name in (
            "idx_maintenance_work_order_task_steps_confirmed_by",
            "idx_maintenance_work_order_task_steps_completed_by",
            "idx_maintenance_work_order_task_steps_status",
            "idx_maintenance_work_order_task_steps_task",
            "idx_maintenance_work_order_task_steps_org",
        ):
            if _has_index("maintenance_work_order_task_steps", index_name):
                op.drop_index(index_name, table_name="maintenance_work_order_task_steps")
        op.drop_table("maintenance_work_order_task_steps")
