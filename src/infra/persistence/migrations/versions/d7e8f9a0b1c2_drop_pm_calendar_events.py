"""drop unused PM calendar_events table

The PM-scoped "calendar event" agenda feature (CalendarEvent domain class,
CalendarService) had zero UI/API consumers and has been removed from the
codebase. This drops its now-orphaned table.

Revision ID: d7e8f9a0b1c2
Revises: c1e2a3n4u5p6
Create Date: 2026-08-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "d7e8f9a0b1c2"
down_revision = "c1e2a3n4u5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_clandar_project", table_name="calendar_events")
    op.drop_index("idx_calendar_start_end", table_name="calendar_events")
    op.drop_table("calendar_events")


def downgrade() -> None:
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_calendar_start_end", "calendar_events", ["start_date", "end_date"], unique=False)
    op.create_index("idx_clandar_project", "calendar_events", ["project_id"], unique=False)
