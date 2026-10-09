"""Data correction: calendar_working_rules rows whose end_time is
inconsistent with their own start_time + break_minutes + hours_override.

Revision ID: d2a4f7b9c6e3
Revises: c7d8e9f0a1b2
Create Date: 2026-10-07 00:00:00.000000

CalendarWorkingRule.compute_hours() returns hours_override unconditionally
when it is set, which silently masked a bootstrap bug: some working-day
rows were seeded with start_time=08:00, break_minutes=60, hours_override=8.0
but end_time=16:00 -- a window that only actually spans 7 net hours, not 8.
compute_hours() reported the (correct) overridden 8.0, so nothing surfaced
until the Month view started rendering the raw start_time/end_time pair
directly. The fix (seeding end_time consistently with start + hours +
break) is already in PlatformCalendarService._seed_default_working_rules;
this migration repairs rows seeded before that fix existed.

Only rows matching the exact buggy signature are touched: is_working_day,
start_time=08:00:00, end_time=16:00:00, break_minutes=60, hours_override=8.0.
end_time is corrected to 17:00:00 (08:00 + 8h + 60min break), matching what
the current seed path already produces for new/re-seeded calendars.
"""
from collections.abc import Sequence
from datetime import time

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2a4f7b9c6e3"
down_revision: str | Sequence[str] | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BUGGY_START = time(8)
_BUGGY_END = time(16)
_CORRECTED_END = time(17)
_BUGGY_BREAK_MINUTES = 60
_BUGGY_HOURS_OVERRIDE = 8.0


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE calendar_working_rules
            SET end_time = :corrected_end
            WHERE is_working_day IS TRUE
              AND start_time = :buggy_start
              AND end_time = :buggy_end
              AND break_minutes = :buggy_break_minutes
              AND hours_override = :buggy_hours_override
            """
        ).bindparams(
            sa.bindparam("corrected_end", _CORRECTED_END, type_=sa.Time()),
            sa.bindparam("buggy_start", _BUGGY_START, type_=sa.Time()),
            sa.bindparam("buggy_end", _BUGGY_END, type_=sa.Time()),
            buggy_break_minutes=_BUGGY_BREAK_MINUTES,
            buggy_hours_override=_BUGGY_HOURS_OVERRIDE,
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE calendar_working_rules
            SET end_time = :buggy_end
            WHERE is_working_day IS TRUE
              AND start_time = :buggy_start
              AND end_time = :corrected_end
              AND break_minutes = :buggy_break_minutes
              AND hours_override = :buggy_hours_override
            """
        ).bindparams(
            sa.bindparam("buggy_end", _BUGGY_END, type_=sa.Time()),
            sa.bindparam("buggy_start", _BUGGY_START, type_=sa.Time()),
            sa.bindparam("corrected_end", _CORRECTED_END, type_=sa.Time()),
            buggy_break_minutes=_BUGGY_BREAK_MINUTES,
            buggy_hours_override=_BUGGY_HOURS_OVERRIDE,
        )
    )
