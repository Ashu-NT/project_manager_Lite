"""Backfill a default (Global-tier) calendar for every organization that
predates OrganizationService creating one transactionally at organization-
creation time.

Revision ID: b54546fc740c
Revises: 5555a14faf88
Create Date: 2026-09-22 15:10:00.000000

Establishes the invariant "every organization has exactly one default
calendar" for organizations that already existed before that invariant was
enforced at creation time. Idempotent: an organization that already has a
GLOBAL-type platform_calendars row is left untouched (including one a
client has since edited -- this only ever fills a genuine gap, never
overwrites). Seeds the same Mon-Fri 08:00-17:00 / 60-minute-break default
working week EnterpriseCalendarService.ensure_global_calendar() seeds for a
fresh install.
"""
from collections.abc import Sequence
from datetime import datetime, time, timezone
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b54546fc740c'
down_revision: str | Sequence[str] | None = '5555a14faf88'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_WORKING_WEEKDAYS = frozenset({0, 1, 2, 3, 4})


def upgrade() -> None:
    connection = op.get_bind()

    calendars = sa.table(
        "platform_calendars",
        sa.column("id", sa.String()),
        sa.column("tenant_id", sa.String()),
        sa.column("organization_id", sa.String()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("calendar_type", sa.String()),
        sa.column("timezone", sa.String()),
        sa.column("is_default", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("priority", sa.Integer()),
        sa.column("version", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    working_rules = sa.table(
        "calendar_working_rules",
        sa.column("id", sa.String()),
        sa.column("calendar_id", sa.String()),
        sa.column("weekday", sa.Integer()),
        sa.column("is_working_day", sa.Boolean()),
        sa.column("start_time", sa.Time()),
        sa.column("end_time", sa.Time()),
        sa.column("break_minutes", sa.Integer()),
        sa.column("hours_override", sa.Float()),
        sa.column("priority", sa.Integer()),
    )

    missing = connection.execute(
        sa.text(
            "SELECT o.id, o.tenant_id FROM organizations o "
            "LEFT JOIN platform_calendars c "
            "ON c.organization_id = o.id AND c.calendar_type = 'GLOBAL' "
            "WHERE c.id IS NULL"
        )
    ).fetchall()

    now = datetime.now(timezone.utc)
    for organization_id, tenant_id in missing:
        calendar_id = f"backfill-{uuid4().hex[:12]}"
        op.execute(
            calendars.insert().values(
                id=calendar_id,
                tenant_id=tenant_id,
                organization_id=organization_id,
                code="GLOBAL",
                name="Global Calendar",
                description="Organization-wide default working calendar.",
                calendar_type="GLOBAL",
                timezone="UTC",
                is_default=True,
                is_active=True,
                priority=0,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        for weekday in range(7):
            is_working = weekday in _WORKING_WEEKDAYS
            op.execute(
                working_rules.insert().values(
                    id=uuid4().hex,
                    calendar_id=calendar_id,
                    weekday=weekday,
                    is_working_day=is_working,
                    start_time=time(8, 0) if is_working else None,
                    end_time=time(17, 0) if is_working else None,
                    break_minutes=60 if is_working else 0,
                    hours_override=8.0 if is_working else None,
                    priority=0,
                )
            )


def downgrade() -> None:
    # Deliberately a no-op: a backfilled calendar is indistinguishable from
    # one a client has since edited (same table, no provenance column), so
    # there's no safe way to identify and remove only the rows this
    # migration created without risking deleting a client's real edits.
    pass
