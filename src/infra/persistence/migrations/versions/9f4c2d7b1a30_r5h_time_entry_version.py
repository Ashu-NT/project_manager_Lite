"""R5H compatibility repair for TimeEntry optimistic concurrency.

Fresh databases already receive this column from the pre-release baseline. The
guarded revision repairs databases stamped before that baseline was updated.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "9f4c2d7b1a30"
down_revision: str | Sequence[str] | None = "d72f4a8c91be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_version_column() -> bool:
    inspector = sa.inspect(op.get_bind())
    if "time_entries" not in inspector.get_table_names():
        return False
    return any(
        column["name"] == "version"
        for column in inspector.get_columns("time_entries")
    )


def upgrade() -> None:
    if _has_version_column():
        return
    with op.batch_alter_table("time_entries") as batch_op:
        batch_op.add_column(
            sa.Column("version", sa.Integer(), server_default="1", nullable=False)
        )


def downgrade() -> None:
    if not _has_version_column():
        return
    with op.batch_alter_table("time_entries") as batch_op:
        batch_op.drop_column("version")
