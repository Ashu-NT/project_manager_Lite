"""Calendar assignment integrity: prevent two simultaneous unbounded
(no effective_from/effective_to) calendar overrides for the same Site/
Department/Employee target.

Revision ID: c7d8e9f0a1b2
Revises: a1f2b3c4d5e6
Create Date: 2026-10-06 00:00:00.000000

Multiple assignment rows per target are intentional (scheduled future/
historical calendar changes, resolved by at_date + priority -- see
SqlAlchemyCalendarAssignmentRepository.get_site_assignment and its
Department/Employee equivalents). What must never happen is two rows for
the same target with no effective window at all (both NULL/NULL, i.e.
"always in effect"), which makes resolution ambiguous. Date-bounded overlap
is enforced at the application/repository layer instead (see
_assert_no_overlapping_assignment), since a portable SQL CHECK/EXCLUDE
constraint for arbitrary date-range overlap isn't available on SQLite.

Verified against the real dev DB before writing this migration: zero
existing rows in any of the three assignment tables, so this is a pure
forward-looking constraint with no backfill/conflict concern.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: str | Sequence[str] | None = 'a1f2b3c4d5e6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEXES = (
    ("ux_site_cal_assign_unbounded", "site_calendar_assignments", "site_id"),
    ("ux_dept_cal_assign_unbounded", "department_calendar_assignments", "department_id"),
    ("ux_emp_cal_assign_unbounded", "employee_calendar_assignments", "employee_id"),
)


def upgrade() -> None:
    for index_name, table_name, column_name in _INDEXES:
        op.create_index(
            index_name,
            table_name,
            [column_name],
            unique=True,
            sqlite_where=sa.text("effective_from IS NULL AND effective_to IS NULL"),
            postgresql_where=sa.text("effective_from IS NULL AND effective_to IS NULL"),
        )


def downgrade() -> None:
    for index_name, table_name, _column_name in _INDEXES:
        op.drop_index(index_name, table_name=table_name)
