"""harden task comment concurrency and moderation evidence

Revision ID: i7j8k9l0m1n2
Revises: h6i7j8k9l0m1
Create Date: 2026-08-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "i7j8k9l0m1n2"
down_revision = "h6i7j8k9l0m1"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "task_comments" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("task_comments")}


def upgrade() -> None:
    columns = _columns()
    if not columns:
        return
    with op.batch_alter_table("task_comments") as batch_op:
        if "deleted_by_user_id" not in columns:
            batch_op.add_column(sa.Column("deleted_by_user_id", sa.String(), nullable=True))
        if "deletion_reason" not in columns:
            batch_op.add_column(sa.Column("deletion_reason", sa.Text(), nullable=True))
        if "version" not in columns:
            batch_op.add_column(
                sa.Column("version", sa.Integer(), nullable=False, server_default="1")
            )


def downgrade() -> None:
    columns = _columns()
    if not columns:
        return
    with op.batch_alter_table("task_comments") as batch_op:
        if "version" in columns:
            batch_op.drop_column("version")
        if "deletion_reason" in columns:
            batch_op.drop_column("deletion_reason")
        if "deleted_by_user_id" in columns:
            batch_op.drop_column("deleted_by_user_id")
