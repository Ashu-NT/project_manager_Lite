"""Employee.organization_id becomes required -- every real construction path
already resolves the active organization before persisting an Employee;
this makes that operational reality a precise, enforced invariant instead of
a nullable column nothing actually leaves null.

Revision ID: a3f6b1d9c852
Revises: e2a5c8f14d63
Create Date: 2026-09-30 00:00:00.000000

There is no safe way to infer a missing organization_id (unlike
department_id, which could be inferred when its own organization had
exactly one department) -- if any employee has no organization_id, this
migration reports the affected rows and raises rather than guessing.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a3f6b1d9c852'
down_revision: str | Sequence[str] | None = 'e2a5c8f14d63'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "employees"


def upgrade() -> None:
    connection = op.get_bind()

    remaining = connection.execute(
        sa.text("SELECT id, employee_code FROM employees WHERE organization_id IS NULL")
    ).fetchall()
    if remaining:
        rows = ", ".join(f"{row[1]} ({row[0]})" for row in remaining)
        raise RuntimeError(
            "Cannot make employees.organization_id required: the following employees have no "
            f"organization and none can be safely inferred -- assign one manually, then re-run "
            f"this migration: {rows}"
        )

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.alter_column(
            "organization_id",
            existing_type=sa.String(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.alter_column(
            "organization_id",
            existing_type=sa.String(),
            nullable=True,
        )
