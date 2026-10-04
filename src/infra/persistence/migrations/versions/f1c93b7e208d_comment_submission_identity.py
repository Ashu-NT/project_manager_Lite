"""Persist immutable comment submission fingerprints for replay detection."""

import sqlalchemy as sa
from alembic import op

revision = "f1c93b7e208d"
down_revision = "e8b42c1d90af"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("task_comments") as batch:
        batch.add_column(
            sa.Column(
                "submission_hash", sa.String(length=64), nullable=False,
                server_default="",
            )
        )


def downgrade():
    with op.batch_alter_table("task_comments") as batch:
        batch.drop_column("submission_hash")
