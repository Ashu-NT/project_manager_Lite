"""Use canonical numeric storage for PM baseline money and assignment hours.

Revision ID: pfnum_d8_002
Revises: pfnum_d8_001
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "pfnum_d8_002"
down_revision = "pfnum_d8_001"
branch_labels = None
depends_on = None

_MONEY = sa.Numeric(precision=19, scale=4)
_QUANTITY = sa.Numeric(precision=19, scale=6)


def _alter(
    table_name: str,
    column_name: str,
    *,
    source_type: sa.types.TypeEngine,
    target_type: sa.types.TypeEngine,
) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=source_type,
            type_=target_type,
            existing_nullable=False,
        )


def upgrade() -> None:
    _alter(
        "baseline_tasks",
        "baseline_planned_cost",
        source_type=sa.Float(),
        target_type=_MONEY,
    )
    _alter(
        "baseline_variance_records",
        "cost_variance",
        source_type=sa.Float(),
        target_type=_MONEY,
    )
    _alter(
        "task_assignments",
        "hours_logged",
        source_type=sa.Float(),
        target_type=_QUANTITY,
    )


def downgrade() -> None:
    _alter(
        "task_assignments",
        "hours_logged",
        source_type=_QUANTITY,
        target_type=sa.Float(),
    )
    _alter(
        "baseline_variance_records",
        "cost_variance",
        source_type=_MONEY,
        target_type=sa.Float(),
    )
    _alter(
        "baseline_tasks",
        "baseline_planned_cost",
        source_type=_MONEY,
        target_type=sa.Float(),
    )

