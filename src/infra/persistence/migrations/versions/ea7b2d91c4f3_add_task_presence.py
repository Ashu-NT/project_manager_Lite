"""add task presence table

Revision ID: ea7b2d91c4f3
Revises: c8e4a6b2d1f3
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa


revision = "ea7b2d91c4f3"
down_revision = "c8e4a6b2d1f3"
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
    if not _has_table("task_presence"):
        op.create_table(
            "task_presence",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("task_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("username", sa.String(length=128), nullable=False),
            sa.Column("display_name", sa.String(length=256), nullable=True),
            sa.Column("activity", sa.String(length=32), nullable=False, server_default="reviewing"),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("task_id", "username", name="ux_task_presence_task_username"),
        )

    if not _has_index("task_presence", "idx_task_presence_task"):
        op.create_index("idx_task_presence_task", "task_presence", ["task_id"], unique=False)
    if not _has_index("task_presence", "idx_task_presence_seen"):
        op.create_index("idx_task_presence_seen", "task_presence", ["last_seen_at"], unique=False)


def downgrade() -> None:
    if _has_index("task_presence", "idx_task_presence_seen"):
        op.drop_index("idx_task_presence_seen", table_name="task_presence")
    if _has_index("task_presence", "idx_task_presence_task"):
        op.drop_index("idx_task_presence_task", table_name="task_presence")
    if _has_table("task_presence"):
        op.drop_table("task_presence")
