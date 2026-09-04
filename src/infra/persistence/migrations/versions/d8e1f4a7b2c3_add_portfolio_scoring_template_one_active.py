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
    connection.execute(
        sa.text(
            """
            UPDATE portfolio_scoring_templates
            SET is_active = 0
            WHERE is_active = 1
              AND id NOT IN (
                  SELECT keeper.id FROM (
                      SELECT t.id,
                             ROW_NUMBER() OVER (
                                 PARTITION BY t.organization_id
                                 ORDER BY t.updated_at DESC, t.id ASC
                             ) AS rn
                      FROM portfolio_scoring_templates t
                      WHERE t.is_active = 1
                  ) AS keeper
                  WHERE keeper.rn = 1
              )
            """
        )
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
