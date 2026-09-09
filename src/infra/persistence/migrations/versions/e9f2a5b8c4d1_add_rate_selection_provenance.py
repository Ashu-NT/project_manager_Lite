"""add immutable rate-selection provenance

Revision ID: e9f2a5b8c4d1
Revises: d8e1f4a7b2c3
Create Date: 2026-09-09

Existing rows remain nullable because their exact historical line version and
modifier cannot be reconstructed truthfully from mutable current Rate Lines.
New Finance consumers populate these columns from RateSelectionSnapshot.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e9f2a5b8c4d1"
down_revision: Union[str, Sequence[str], None] = "d8e1f4a7b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = {
    "project_approved_time_labor_postings": "labor",
    "project_finance_planned_cost_lines": "planned_cost",
    "project_billing_preparation_lines": "billing_line",
}


def upgrade() -> None:
    for table, constraint_prefix in _TABLES.items():
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("rate_line_version", sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column("rate_modifier", sa.String(length=24), nullable=True))
            batch_op.add_column(
                sa.Column(
                    "rate_modifier_multiplier",
                    sa.Numeric(precision=19, scale=8),
                    nullable=True,
                )
            )
            batch_op.create_check_constraint(
                f"ck_{constraint_prefix}_rate_line_version",
                "rate_line_version IS NULL OR rate_line_version >= 1",
            )
            batch_op.create_check_constraint(
                f"ck_{constraint_prefix}_rate_modifier",
                "rate_modifier_multiplier IS NULL OR "
                "(rate_modifier IS NOT NULL AND rate_modifier_multiplier >= 0)",
            )


def downgrade() -> None:
    for table, constraint_prefix in reversed(tuple(_TABLES.items())):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(
                f"ck_{constraint_prefix}_rate_modifier", type_="check"
            )
            batch_op.drop_constraint(
                f"ck_{constraint_prefix}_rate_line_version", type_="check"
            )
            batch_op.drop_column("rate_modifier_multiplier")
            batch_op.drop_column("rate_modifier")
            batch_op.drop_column("rate_line_version")
