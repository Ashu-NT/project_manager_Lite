"""Employee<->User becomes optional one-to-one: a User account cannot be
linked to more than one Employee. Employee stays the owning reference
(Employee.user_id); User carries no reciprocal column.

Revision ID: c9a5f2d8b647
Revises: b7d2e4a691f3
Create Date: 2026-09-30 00:00:02.000000

Multiple Employees with a NULL user_id are always fine (the partial index
only constrains non-null values) -- only a User linked to two or more
Employees is a real conflict, reported (never silently resolved) before the
constraint is added.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c9a5f2d8b647'
down_revision: str | Sequence[str] | None = 'b7d2e4a691f3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "employees"


def upgrade() -> None:
    connection = op.get_bind()

    duplicates = connection.execute(
        sa.text(
            """
            SELECT user_id, COUNT(*) AS c
            FROM employees
            WHERE user_id IS NOT NULL
            GROUP BY user_id
            HAVING c > 1
            """
        )
    ).fetchall()
    if duplicates:
        rows = ", ".join(f"user {row[0]} ({row[1]} employees)" for row in duplicates)
        raise RuntimeError(
            "Cannot enforce one Employee per User: the following User accounts are already "
            f"linked to more than one Employee -- resolve them manually, then re-run this "
            f"migration: {rows}"
        )

    op.drop_index("idx_employees_user", table_name=_TABLE)
    op.create_index(
        "idx_employees_user",
        _TABLE,
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_employees_user", table_name=_TABLE)
    op.create_index("idx_employees_user", _TABLE, ["user_id"], unique=False)
