"""Use canonical numeric storage for remaining PM rate, quantity, and budget fields.

Revision ID: pfnum_d8_001
Revises: pfchg_d2_001
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "pfnum_d8_001"
down_revision = "pfchg_d2_001"
branch_labels = None
depends_on = None

_MONEY = sa.Numeric(precision=19, scale=4)
_RATE = sa.Numeric(precision=19, scale=8)
_QUANTITY = sa.Numeric(precision=19, scale=6)


def _alter(
    table_name: str,
    column_name: str,
    *,
    source_type: sa.types.TypeEngine,
    target_type: sa.types.TypeEngine,
    nullable: bool,
) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=source_type,
            type_=target_type,
            existing_nullable=nullable,
        )


def upgrade() -> None:
    _alter(
        "resources",
        "hourly_rate",
        source_type=sa.Float(),
        target_type=_RATE,
        nullable=False,
    )
    _alter(
        "project_resources",
        "hourly_rate",
        source_type=sa.Float(),
        target_type=_RATE,
        nullable=True,
    )
    _alter(
        "project_resources",
        "planned_hours",
        source_type=sa.Float(),
        target_type=_QUANTITY,
        nullable=False,
    )
    _alter(
        "portfolio_intake_items",
        "requested_budget",
        source_type=sa.Float(),
        target_type=_MONEY,
        nullable=False,
    )
    _alter(
        "portfolio_scenarios",
        "budget_limit",
        source_type=sa.Float(),
        target_type=_MONEY,
        nullable=True,
    )


def downgrade() -> None:
    _alter(
        "portfolio_scenarios",
        "budget_limit",
        source_type=_MONEY,
        target_type=sa.Float(),
        nullable=True,
    )
    _alter(
        "portfolio_intake_items",
        "requested_budget",
        source_type=_MONEY,
        target_type=sa.Float(),
        nullable=False,
    )
    _alter(
        "project_resources",
        "planned_hours",
        source_type=_QUANTITY,
        target_type=sa.Float(),
        nullable=False,
    )
    _alter(
        "project_resources",
        "hourly_rate",
        source_type=_RATE,
        target_type=sa.Float(),
        nullable=True,
    )
    _alter(
        "resources",
        "hourly_rate",
        source_type=_RATE,
        target_type=sa.Float(),
        nullable=False,
    )

