"""add budget predecessor lineage

Revision ID: a61d8c4f2b70
Revises: f3c89cac079d
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a61d8c4f2b70"
down_revision: Union[str, Sequence[str], None] = "f3c89cac079d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("project_finance_budgets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("predecessor_budget_id", sa.String(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_pf_budgets_scoped_predecessor",
            "project_finance_budgets",
            [
                "tenant_id",
                "organization_id",
                "project_id",
                "predecessor_budget_id",
            ],
            ["tenant_id", "organization_id", "project_id", "id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("project_finance_budgets", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_pf_budgets_scoped_predecessor", type_="foreignkey"
        )
        batch_op.drop_column("predecessor_budget_id")
