"""add task name snapshot to baseline tasks

Revision ID: 7d3fd7fd42bd
Revises: ef8d1d37eabf
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7d3fd7fd42bd"
down_revision = "ef8d1d37eabf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("baseline_tasks", sa.Column("task_name", sa.String(), nullable=True))
    op.execute(
        """
        UPDATE baseline_tasks
        SET task_name = (
            SELECT tasks.name
            FROM tasks
            WHERE tasks.id = baseline_tasks.task_id
        )
        WHERE task_name IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("baseline_tasks", "task_name")
