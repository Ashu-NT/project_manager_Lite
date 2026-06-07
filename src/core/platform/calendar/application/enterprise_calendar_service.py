"""Enterprise calendar CRUD service — Platform owned."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.core.platform.auth.authorization import require_permission
from src.core.platform.calendar.contracts import (
    CalendarAssignmentRepository,
    CalendarExceptionRepository,
    CalendarWorkingRuleRepository,
    PlatformCalendarRepository,
)
from src.core.platform.calendar.domain.enterprise_calendar import (
    CalendarType,
    PlatformCalendar,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError


_VALID_CALENDAR_TYPES = {t.value for t in CalendarType}
_VALID_GRANULARITIES = {5, 10, 15, 30, 60}
logger = logging.getLogger(__name__)


def _resolve_username(user_session) -> str | None:
    if user_session is None:
        return None
    direct = getattr(user_session, "username", None)
    if isinstance(direct, str):
        return direct
    principal = getattr(user_session, "principal", None)
    if principal is not None:
        via_principal = getattr(principal, "username", None)
        if isinstance(via_principal, str):
            return via_principal
    return None


class EnterpriseCalendarService:
    """Platform-owned CRUD service for PlatformCalendar entities."""

    def __init__(
        self,
        session: Session,
        calendar_repo: PlatformCalendarRepository,
        assignment_repo: CalendarAssignmentRepository,
        organization_repo,
        rule_repo: CalendarWorkingRuleRepository | None = None,
        exception_repo: CalendarExceptionRepository | None = None,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._assignment_repo = assignment_repo
        self._organization_repo = organization_repo
        self._rule_repo = rule_repo
        self._exception_repo = exception_repo
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

        username = _resolve_username(self._user_session)
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
        username = _resolve_username(self._user_session)
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

    def ensure_global_calendar(
        self,
        organization_id: str,
        working_calendar_repo=None,
    ) -> PlatformCalendar:
        """
        Bootstrap: create the GLOBAL enterprise calendar for an org if it doesn't exist.

        If working_calendar_repo is provided and a legacy 'default' working_calendar exists,
        its working-day rules and holidays are migrated into the new enterprise tables so
        no calendar behavior is lost. The legacy tables remain until the Alembic migration
        drops them explicitly.
        """
        existing = self._calendar_repo.get_global(organization_id)
        if existing is not None:
            self._ensure_working_rules(existing.id, working_calendar_repo)
            self._session.commit()
            return existing

        now = datetime.utcnow()
        cal = PlatformCalendar(
            id=f"global-{organization_id[:8]}",
            organization_id=organization_id,
            code="GLOBAL",
            name="Global Calendar",
            calendar_type=CalendarType.GLOBAL.value,
            timezone="UTC",
            description="Organization-wide default working calendar (migrated from legacy).",
            is_default=True,
            is_active=True,
            priority=0,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._calendar_repo.add(cal)
        self._session.flush()

        # Always seed working rules — migrates from legacy if repo provided,
        # otherwise seeds Mon-Fri 08:00-17:00 defaults (fresh install path).
        self._migrate_legacy_calendar(cal.id, working_calendar_repo)

        self._session.commit()
        return cal

    def _ensure_working_rules(self, enterprise_cal_id: str, working_calendar_repo) -> None:
        if self._rule_repo is None:
            logger.warning(
                "Cannot verify global calendar working rules because rule repository is unavailable calendar_id=%s",
                enterprise_cal_id,
            )
            return
        existing_rules = self._rule_repo.list_for_calendar(enterprise_cal_id)
        if existing_rules:
            return
        logger.warning(
            "Global calendar has no working rules; seeding default working week calendar_id=%s",
            enterprise_cal_id,
        )
        self._migrate_legacy_calendar(enterprise_cal_id, working_calendar_repo)

    def _migrate_legacy_calendar(self, enterprise_cal_id: str, working_calendar_repo) -> None:
        """
        Migrate legacy working_calendars + holidays into enterprise tables.
        Falls back to Mon-Fri 08:00-17:00 defaults when no legacy data exists.
        Safe to call multiple times — skips if working rules already exist.
        """
        from src.core.platform.calendar.domain.enterprise_calendar import (
            CalendarWorkingRule,
            CalendarException,
            ExceptionType,
            ImpactType,
        )
        from datetime import time

        if self._rule_repo is None:
            logger.warning(
                "Skipping enterprise calendar working rule seed because rule repository is unavailable calendar_id=%s",
                enterprise_cal_id,
            )
            return

        # Load legacy calendar (may be None for fresh installs)
        try:
            legacy_cal = working_calendar_repo.get_default() if working_calendar_repo else None
        except Exception:
            legacy_cal = None

        # Migrate working rules — use legacy data if available, otherwise default Mon-Fri
        try:
            existing_rules = self._rule_repo.list_for_calendar(enterprise_cal_id)
            if not existing_rules:
                working_days = (legacy_cal.working_days if legacy_cal else None) or {0, 1, 2, 3, 4}
                hours = float((legacy_cal.hours_per_day if legacy_cal else None) or 8.0)
                end_hour = 8 + int(hours)
                end_minute = int((hours % 1) * 60)
                for weekday in range(7):
                    is_working = weekday in working_days
                    rule = CalendarWorkingRule.create(
                        calendar_id=enterprise_cal_id,
                        weekday=weekday,
                        is_working_day=is_working,
                        start_time=time(8, 0) if is_working else None,
                        end_time=time(min(end_hour, 23), end_minute) if is_working else None,
                        break_minutes=60 if is_working else 0,
                        hours_override=hours if is_working else None,
                    )
                    self._rule_repo.save(rule)
        except Exception:
            logger.exception(
                "Failed to seed enterprise calendar working rules calendar_id=%s",
                enterprise_cal_id,
            )
            raise

        # Migrate holidays into calendar_exceptions (only when legacy data exists)
        try:
            if legacy_cal is None or working_calendar_repo is None or self._exception_repo is None:
                return
            existing_exceptions = self._exception_repo.list_for_calendar(enterprise_cal_id)
            existing_dates = {e.exception_date for e in existing_exceptions}
            holidays = working_calendar_repo.list_holidays(legacy_cal.id)
            for holiday in holidays:
                if holiday.date not in existing_dates:
                    exc = CalendarException.create(
                        calendar_id=enterprise_cal_id,
                        exception_date=holiday.date,
                        exception_type=ExceptionType.HOLIDAY.value,
                        name=holiday.name or "Holiday",
                        impact_type=ImpactType.UNAVAILABLE.value,
                    )
                    self._exception_repo.add(exc)
        except Exception:
            logger.exception(
                "Failed to migrate enterprise calendar exceptions calendar_id=%s",
                enterprise_cal_id,
            )
            raise

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
