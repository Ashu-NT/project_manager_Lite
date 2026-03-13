"""add user-backed task mention fields

Revision ID: d4c9e2a17f6b
Revises: b18e7b3f21c4, c2b7f1ab61de
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa


revision = "d4c9e2a17f6b"
down_revision = ("b18e7b3f21c4", "c2b7f1ab61de")
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("task_comments") as batch:
        batch.add_column(
            sa.Column(
                "mentioned_user_ids_json",
                sa.Text(),
                nullable=False,
                server_default="[]",
            )
        )
        batch.add_column(
            sa.Column(
                "read_by_user_ids_json",
                sa.Text(),
                nullable=False,
                server_default="[]",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("task_comments") as batch:
        batch.drop_column("read_by_user_ids_json")
        batch.drop_column("mentioned_user_ids_json")
