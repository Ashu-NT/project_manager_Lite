"""add task comments and time entries

Revision ID: c2b7f1ab61de
Revises: 9a5d2e8bf4c1
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa


revision = "c2b7f1ab61de"
down_revision = "9a5d2e8bf4c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "time_entries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("assignment_id", sa.String(), sa.ForeignKey("task_assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("author_user_id", sa.String(), nullable=True),
        sa.Column("author_username", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_time_entries_assignment", "time_entries", ["assignment_id"])
    op.create_index("idx_time_entries_date", "time_entries", ["entry_date"])

    op.create_table(
        "task_comments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("task_id", sa.String(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_user_id", sa.String(), nullable=True),
        sa.Column("author_username", sa.String(length=128), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mentions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("attachments_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("read_by_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_task_comments_task", "task_comments", ["task_id"])
    op.create_index("idx_task_comments_created", "task_comments", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_task_comments_created", table_name="task_comments")
    op.drop_index("idx_task_comments_task", table_name="task_comments")
    op.drop_table("task_comments")

    op.drop_index("idx_time_entries_date", table_name="time_entries")
    op.drop_index("idx_time_entries_assignment", table_name="time_entries")
    op.drop_table("time_entries")
