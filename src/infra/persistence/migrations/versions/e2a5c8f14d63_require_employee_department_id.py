"""Employee.department_id becomes required -- every Employee belongs to
exactly one Department.

Revision ID: e2a5c8f14d63
Revises: c9e6a3b1f847
Create Date: 2026-09-29 00:00:00.000000

Backfills an employee's missing department_id only when its organization
has exactly one Department -- the one case where the correct value is
unambiguous. Any employee whose organization has zero or more than one
Department (so no single Department can be safely inferred) is left
untouched and this migration raises, listing the affected employee ids,
rather than guessing -- resolve those rows manually and re-run.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e2a5c8f14d63'
down_revision: str | Sequence[str] | None = 'c9e6a3b1f847'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "employees"


def upgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            UPDATE employees
            SET department_id = (
                SELECT d.id FROM departments d
                WHERE d.organization_id = employees.organization_id
            )
            WHERE employees.department_id IS NULL
              AND (
                SELECT COUNT(*) FROM departments d
                WHERE d.organization_id = employees.organization_id
              ) = 1
            """
        )
    )

    remaining = connection.execute(
        sa.text(
            "SELECT id, employee_code, organization_id FROM employees WHERE department_id IS NULL"
        )
    ).fetchall()
    if remaining:
        rows = ", ".join(f"{row[1]} ({row[0]}, organization {row[2]})" for row in remaining)
        raise RuntimeError(
            "Cannot make employees.department_id required: the following employees have no "
            "department and their organization does not have exactly one department to infer "
            f"it from -- assign a department to each manually, then re-run this migration: {rows}"
        )

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.alter_column(
            "department_id",
            existing_type=sa.String(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.alter_column(
            "department_id",
            existing_type=sa.String(),
            nullable=True,
        )
