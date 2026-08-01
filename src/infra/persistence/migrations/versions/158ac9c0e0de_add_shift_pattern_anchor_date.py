"""add anchor_date to shift_patterns

anchor_date is the rotation cycle's day-0 reference date, needed to resolve
which ShiftPatternDay applies on a given calendar date
((target_date - anchor_date).days % rotation_cycle_days).

Revision ID: 158ac9c0e0de
Revises: d7e8f9a0b1c2
Create Date: 2026-08-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "158ac9c0e0de"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("shift_patterns") as batch_op:
        batch_op.add_column(sa.Column("anchor_date", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("shift_patterns") as batch_op:
        batch_op.drop_column("anchor_date")
