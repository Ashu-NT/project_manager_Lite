"""Add department_id FK column to projects table.

Revision ID: q7r8s9t0u1v2
Revises: pfaudit_p04_001
Create Date: 2026-08-18

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "q7r8s9t0u1v2"
down_revision = "pfaudit_p04_001"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return column in {col["name"] for col in insp.get_columns(table)}


def upgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        if not _has_column("projects", "department_id"):
            batch_op.add_column(
                sa.Column("department_id", sa.String(), nullable=True)
            )

    op.create_index(
        "idx_projects_department_id",
        "projects",
        ["department_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("idx_projects_department_id", table_name="projects")
    with op.batch_alter_table("projects", schema=None) as batch_op:
        if _has_column("projects", "department_id"):
            batch_op.drop_column("department_id")
