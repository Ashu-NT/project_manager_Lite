"""add purchase requisition line version column

Revision ID: c3f6a1b8d9e0
Revises: a61d8c4f2b70
Create Date: 2026-09-02

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3f6a1b8d9e0"
down_revision: str | Sequence[str] | None = "a61d8c4f2b70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("inventory_purchase_requisition_lines", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "version", sa.Integer(), nullable=False, server_default="1"
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("inventory_purchase_requisition_lines", schema=None) as batch_op:
        batch_op.drop_column("version")
