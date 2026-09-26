"""Rename departments.manager_employee_id to head_of_department_employee_id.

Revision ID: d6a3f8c2b951
Revises: c7f2a5d91b48
Create Date: 2026-09-24 09:00:00.000000

The canonical terminology for this relationship is now Head of Department
(HOD), not "Manager"/"Lead" -- pre-release, so the column is renamed in
place rather than adding a second column, and every existing assignment is
carried over automatically since a rename (not a drop+add) preserves the
underlying values. batch_alter_table's column rename carries the existing
foreign key constraint along with it (its local column reference is
updated to the new column name automatically); the constraint is left
under its original name; SQLite does not reliably reflect named
constraints back across a fresh connection (as a later downgrade would),
so this migration does not attempt to rename it explicitly.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd6a3f8c2b951'
down_revision: str | Sequence[str] | None = 'c7f2a5d91b48'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "departments"
_OLD_COLUMN = "manager_employee_id"
_NEW_COLUMN = "head_of_department_employee_id"


def upgrade() -> None:
    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.alter_column(
            _OLD_COLUMN,
            new_column_name=_NEW_COLUMN,
            existing_type=sa.String(),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.alter_column(
            _NEW_COLUMN,
            new_column_name=_OLD_COLUMN,
            existing_type=sa.String(),
            existing_nullable=True,
        )
