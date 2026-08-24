"""add indexed Resource activity correlation

Revision ID: c817a91e5f24
Revises: f3c89cac079d
Create Date: 2026-08-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c817a91e5f24"
down_revision: Union[str, Sequence[str], None] = "f3c89cac079d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("activity_entries", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("related_entity_type", sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column("related_entity_id", sa.String(), nullable=True)
        )
        batch_op.create_index(
            "idx_activity_related",
            ["related_entity_type", "related_entity_id", "timestamp"],
            unique=False,
        )

    with op.batch_alter_table("task_assignments", schema=None) as batch_op:
        batch_op.create_index(
            "idx_task_assignments_resource",
            ["resource_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("task_assignments", schema=None) as batch_op:
        batch_op.drop_index("idx_task_assignments_resource")

    with op.batch_alter_table("activity_entries", schema=None) as batch_op:
        batch_op.drop_index("idx_activity_related")
        batch_op.drop_column("related_entity_id")
        batch_op.drop_column("related_entity_type")
