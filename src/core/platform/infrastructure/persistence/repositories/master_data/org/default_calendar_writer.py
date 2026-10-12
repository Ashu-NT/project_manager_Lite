from __future__ import annotations

from datetime import UTC, datetime, time

from sqlalchemy.orm import Session

from src.core.platform.common.ids import generate_id
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarType,
)
from src.core.platform.infrastructure.persistence.orm.time_management.calendar.enterprise_calendar import (
    CalendarWorkingRuleORM,
    PlatformCalendarORM,
)


class SqlAlchemyOrganizationDefaultCalendarWriter:
    """Seed an organization's default calendar without ambient-org redirection."""

    def add_default_calendar(self, session: Session, organization: Organization) -> None:
        now = datetime.now(UTC)
        calendar_id = f"global-{organization.id[:8]}"
        session.add(
            PlatformCalendarORM(
                id=calendar_id,
                tenant_id=organization.tenant_id,
                organization_id=organization.id,
                code="GLOBAL",
                name="Global Calendar",
                description="Organization-wide default working calendar.",
                calendar_type=CalendarType.GLOBAL.value,
                timezone=organization.timezone_name or "UTC",
                is_default=True,
                is_active=True,
                priority=0,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        for weekday in range(7):
            is_working = weekday < 5
            session.add(
                CalendarWorkingRuleORM(
                    id=generate_id(),
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
