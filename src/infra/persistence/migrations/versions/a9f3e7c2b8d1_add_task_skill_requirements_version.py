"""Add the missing `version` column to task_skill_requirements.

The table's own ORM model (`TaskSkillRequirementORM`) has always declared
`version: Mapped[int]`, and the sibling tables created in the same original
migration (`resource_skills`, `resource_certifications`) both correctly
included a `version` column -- only `task_skill_requirements`'s
`create_table()` in i2j3k4l5m6n7_pm_enterprise_upgrade.py omitted it. Any
query that selects the ORM's full column list (e.g. skill/certification
validation when assigning a resource to a task) fails with
`sqlite3.OperationalError: no such column: task_skill_requirements.version`.

Revision ID: a9f3e7c2b8d1
Revises: q7r8s9t0u1v2
Create Date: 2026-08-19

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "a9f3e7c2b8d1"
down_revision = "q7r8s9t0u1v2"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return column in {col["name"] for col in insp.get_columns(table)}


def upgrade() -> None:
    with op.batch_alter_table("task_skill_requirements", schema=None) as batch_op:
        if not _has_column("task_skill_requirements", "version"):
            batch_op.add_column(
                sa.Column("version", sa.Integer(), nullable=False, server_default="1")
            )


def downgrade() -> None:
    with op.batch_alter_table("task_skill_requirements", schema=None) as batch_op:
        if _has_column("task_skill_requirements", "version"):
            batch_op.drop_column("version")
