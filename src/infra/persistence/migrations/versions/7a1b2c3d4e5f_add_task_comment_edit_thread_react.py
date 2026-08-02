"""add edit/soft-delete/threading/reactions columns to task_comments

Adds parent_comment_id (self-referencing FK, for reply-to threading),
updated_at (edit marker), deleted_at (soft-delete marker), and
reactions_json (emoji -> reactor user_ids) to task_comments.

Revision ID: 7a1b2c3d4e5f
Revises: 4f20c1d95e8f
Create Date: 2026-08-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "7a1b2c3d4e5f"
down_revision = "4f20c1d95e8f"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not _table_exists(inspector, "task_comments"):
        return

    columns = _column_names(inspector, "task_comments")

    if "parent_comment_id" not in columns:
        with op.batch_alter_table("task_comments") as batch_op:
            batch_op.add_column(sa.Column("parent_comment_id", sa.String(), nullable=True))
            batch_op.create_foreign_key(
                "fk_task_comments_parent_comment_id",
                "task_comments",
                ["parent_comment_id"],
                ["id"],
                ondelete="SET NULL",
            )
        inspector = sa.inspect(connection)

    if "updated_at" not in columns:
        op.add_column("task_comments", sa.Column("updated_at", sa.DateTime(), nullable=True))

    if "deleted_at" not in columns:
        op.add_column("task_comments", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    if "reactions_json" not in columns:
        op.add_column(
            "task_comments",
            sa.Column("reactions_json", sa.Text(), nullable=False, server_default="{}"),
        )

    if "idx_task_comments_parent" not in _index_names(inspector, "task_comments"):
        op.create_index("idx_task_comments_parent", "task_comments", ["parent_comment_id"])


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "task_comments"):
        return

    if "idx_task_comments_parent" in _index_names(inspector, "task_comments"):
        op.drop_index("idx_task_comments_parent", table_name="task_comments")

    columns = _column_names(inspector, "task_comments")
    with op.batch_alter_table("task_comments") as batch_op:
        if "parent_comment_id" in columns:
            batch_op.drop_constraint("fk_task_comments_parent_comment_id", type_="foreignkey")
            batch_op.drop_column("parent_comment_id")
        if "updated_at" in columns:
            batch_op.drop_column("updated_at")
        if "deleted_at" in columns:
            batch_op.drop_column("deleted_at")
        if "reactions_json" in columns:
            batch_op.drop_column("reactions_json")
