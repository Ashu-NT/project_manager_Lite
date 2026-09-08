"""add portfolio scoring template one-active-per-organization invariant

Revision ID: d8e1f4a7b2c3
Revises: c3f6a1b8d9e0
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8e1f4a7b2c3"
down_revision: Union[str, Sequence[str], None] = "c3f6a1b8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    templates = sa.table(
        "portfolio_scoring_templates",
        sa.column("id", sa.String()),
        sa.column("organization_id", sa.String()),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("is_active", sa.Boolean()),
    )
    ranked = (
        sa.select(
            templates.c.id,
            sa.func.row_number()
            .over(
                partition_by=templates.c.organization_id,
                order_by=(templates.c.updated_at.desc(), templates.c.id.asc()),
            )
            .label("rn"),
        )
        .where(templates.c.is_active.is_(True))
        .subquery("ranked_active_portfolio_scoring_templates")
    )
    keeper_ids = sa.select(ranked.c.id).where(ranked.c.rn == 1)
    connection.execute(
        sa.update(templates)
        .where(
            templates.c.is_active.is_(True),
            templates.c.id.not_in(keeper_ids),
        )
        .values(is_active=False)
    )

    with op.batch_alter_table("portfolio_scoring_templates", schema=None) as batch_op:
        batch_op.create_index(
            "uq_portfolio_scoring_one_active_per_org",
            ["organization_id"],
            unique=True,
            postgresql_where=sa.text("is_active = true"),
            sqlite_where=sa.text("is_active = 1"),
        )


def downgrade() -> None:
    with op.batch_alter_table("portfolio_scoring_templates", schema=None) as batch_op:
        batch_op.drop_index(
            "uq_portfolio_scoring_one_active_per_org",
            postgresql_where=sa.text("is_active = true"),
            sqlite_where=sa.text("is_active = 1"),
        )
