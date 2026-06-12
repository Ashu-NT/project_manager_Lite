"""Drop legacy working_calendars and holidays tables.

These tables are replaced by the enterprise calendar system (migration n7o8p9q0r1s2):
  working_calendars  → platform_calendars (type=GLOBAL) + calendar_working_rules
  holidays           → calendar_exceptions (type=HOLIDAY, impact=UNAVAILABLE)

Data is migrated automatically at application startup by
EnterpriseCalendarService.ensure_global_calendar() which reads from
working_calendars/holidays and creates the equivalent enterprise records before
this migration drops the legacy tables.

Revision ID: o8p9q0r1s2t3
Revises: n7o8p9q0r1s2
Create Date: 2026-06-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "o8p9q0r1s2t3"
down_revision = "n7o8p9q0r1s2"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    # Drop FK-referencing table first
    if _index_exists("holidays", "idx_holiday_calendar_date"):
        op.drop_index("idx_holiday_calendar_date", table_name="holidays")
    if _table_exists("holidays"):
        op.drop_table("holidays")

    # Drop the legacy working calendars master table
    if _table_exists("working_calendars"):
        op.drop_table("working_calendars")


def downgrade() -> None:
    # Recreate legacy tables for rollback (data will be empty — re-import from enterprise tables if needed)
    if not _table_exists("working_calendars"):
        op.create_table(
            "working_calendars",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("working_days", sa.String(), nullable=False, server_default="0,1,2,3,4"),
            sa.Column("hours_per_day", sa.Float(), server_default="8.0"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _table_exists("holidays"):
        op.create_table(
            "holidays",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column(
                "calendar_id",
                sa.String(),
                sa.ForeignKey("working_calendars.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("name", sa.String(), server_default=""),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_holiday_calendar_date", "holidays", ["calendar_id", "date"])
