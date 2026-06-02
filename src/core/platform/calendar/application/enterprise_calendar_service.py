"""Enterprise calendar CRUD service — Platform owned."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.core.platform.auth.authorization import require_permission
from src.core.platform.calendar.contracts import (
    CalendarAssignmentRepository,
    PlatformCalendarRepository,
)
from src.core.platform.calendar.domain.enterprise_calendar import (
    CalendarType,
    PlatformCalendar,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError


_VALID_CALENDAR_TYPES = {t.value for t in CalendarType}
_VALID_GRANULARITIES = {5, 10, 15, 30, 60}


class EnterpriseCalendarService:
    """Platform-owned CRUD service for PlatformCalendar entities."""

    def __init__(
        self,
        session: Session,
        calendar_repo: PlatformCalendarRepository,
        assignment_repo: CalendarAssignmentRepository,
        organization_repo,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._assignment_repo = assignment_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def _active_org_id(self) -> str:
        org = self._organization_repo.get_active()
        if org is None:
            raise BusinessRuleError("No active organization found.")
        return org.id

    def list_calendars(
        self,
        *,
        calendar_type: Optional[str] = None,
        active_only: Optional[bool] = None,
    ) -> list[PlatformCalendar]:
        require_permission(self._user_session, "task.read", operation_label="list calendars")
        org_id = self._active_org_id()
        return self._calendar_repo.list_for_organization(
            org_id, calendar_type=calendar_type, active_only=active_only
        )

    def get_calendar(self, calendar_id: str) -> PlatformCalendar:
        require_permission(self._user_session, "task.read", operation_label="get calendar")
        cal = self._calendar_repo.get(calendar_id)
        if cal is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")
        return cal

    def create_calendar(
        self,
        *,
        code: str,
        name: str,
        calendar_type: str,
        timezone: str = "UTC",
        description: Optional[str] = None,
        base_calendar_id: Optional[str] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
        locale: Optional[str] = None,
        is_default: bool = False,
        effective_from=None,
        effective_to=None,
        priority: int = 0,
    ) -> PlatformCalendar:
        require_permission(
            self._user_session, "task.manage", operation_label="create calendar"
        )
        org_id = self._active_org_id()
        self._validate_type(calendar_type)
        self._validate_effective_dates(effective_from, effective_to)

        existing = self._calendar_repo.get_by_code(org_id, code.strip())
        if existing is not None:
            raise ValidationError(f"Calendar code '{code}' already exists.")

        username = self._user_session.username if self._user_session else None
        cal = PlatformCalendar.create(
            organization_id=org_id,
            code=code.strip(),
            name=name.strip(),
            calendar_type=calendar_type,
            timezone=timezone or "UTC",
            description=description,
            base_calendar_id=base_calendar_id,
            scope_type=scope_type,
            scope_id=scope_id,
            locale=locale,
            is_default=is_default,
            effective_from=effective_from,
            effective_to=effective_to,
            priority=priority,
            created_by=username,
        )
        self._calendar_repo.add(cal)
        self._session.commit()
        return cal

    def update_calendar(
        self,
        calendar_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        timezone: Optional[str] = None,
        locale: Optional[str] = None,
        is_default: Optional[bool] = None,
        is_active: Optional[bool] = None,
        effective_from=None,
        effective_to=None,
        priority: Optional[int] = None,
    ) -> PlatformCalendar:
        require_permission(
            self._user_session, "task.manage", operation_label="update calendar"
        )
        cal = self._calendar_repo.get(calendar_id)
        if cal is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")

        if name is not None:
            cal.name = name.strip()
        if description is not None:
            cal.description = description
        if timezone is not None:
            cal.timezone = timezone
        if locale is not None:
            cal.locale = locale
        if is_default is not None:
            cal.is_default = is_default
        if is_active is not None:
            cal.is_active = is_active
        if effective_from is not None or effective_to is not None:
            self._validate_effective_dates(
                effective_from or cal.effective_from,
                effective_to or cal.effective_to,
            )
            if effective_from is not None:
                cal.effective_from = effective_from
            if effective_to is not None:
                cal.effective_to = effective_to
        if priority is not None:
            cal.priority = priority

        cal.version += 1
        cal.updated_at = datetime.utcnow()
        username = self._user_session.username if self._user_session else None
        cal.updated_by = username
        self._calendar_repo.update(cal)
        self._session.commit()
        return cal

    def delete_calendar(self, calendar_id: str) -> None:
        require_permission(
            self._user_session, "task.manage", operation_label="delete calendar"
        )
        cal = self._calendar_repo.get(calendar_id)
        if cal is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")

        count = self._assignment_repo.count_active_assignments_for_calendar(calendar_id)
        if count > 0:
            raise BusinessRuleError(
                f"Cannot delete calendar '{cal.name}': it is assigned to {count} "
                "site(s), department(s), or employee(s). Remove assignments first."
            )
        self._calendar_repo.delete(calendar_id)
        self._session.commit()

    def ensure_global_calendar(self, organization_id: str) -> PlatformCalendar:
        """Bootstrap: create the GLOBAL calendar for an org if it doesn't exist."""
        existing = self._calendar_repo.get_global(organization_id)
        if existing is not None:
            return existing

        now = datetime.utcnow()
        cal = PlatformCalendar(
            id=f"global-{organization_id[:8]}",
            organization_id=organization_id,
            code="GLOBAL",
            name="Global Calendar",
            calendar_type=CalendarType.GLOBAL.value,
            timezone="UTC",
            description="Organization-wide default working calendar.",
            is_default=True,
            is_active=True,
            priority=0,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._calendar_repo.add(cal)
        self._session.commit()
        return cal

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    def _validate_type(self, calendar_type: str) -> None:
        if calendar_type not in _VALID_CALENDAR_TYPES:
            raise ValidationError(
                f"Invalid calendar_type '{calendar_type}'. "
                f"Valid values: {sorted(_VALID_CALENDAR_TYPES)}"
            )

    def _validate_effective_dates(self, effective_from, effective_to) -> None:
        if effective_from and effective_to and effective_from > effective_to:
            raise ValidationError("effective_from must be before effective_to.")


__all__ = ["EnterpriseCalendarService"]
