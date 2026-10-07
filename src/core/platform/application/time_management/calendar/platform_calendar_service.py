"""Enterprise calendar CRUD service — Platform owned."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import replace
from datetime import date, datetime
from datetime import timezone as zone
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.repositories.time_management.calendar.contracts import (
    CalendarAssignmentRepository,
    CalendarExceptionRepository,
    CalendarWorkingRuleRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarType,
    PlatformCalendar,
)
from src.core.shared.activity import record_activity

_VALID_GRANULARITIES = {5, 10, 15, 30, 60}
logger = logging.getLogger(__name__)


def _resolve_username(user_session: Any) -> str | None:
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


class PlatformCalendarService:
    """Platform-owned CRUD service for PlatformCalendar entities."""

    def __init__(
        self,
        session: Session,
        calendar_repo: PlatformCalendarRepository,
        assignment_repo: CalendarAssignmentRepository,
        organization_repo: Any,
        rule_repo: CalendarWorkingRuleRepository | None = None,
        exception_repo: CalendarExceptionRepository | None = None,
        user_session: Any = None,
        tenant_context_service: TenantContextService | None = None,
        activity_service: Any = None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._assignment_repo = assignment_repo
        self._organization_repo = organization_repo
        self._rule_repo = rule_repo
        self._exception_repo = exception_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        # record_activity(self, ...) looks for this exact attribute name --
        # see src/core/shared/activity/activity_recorder.py.
        self._activity_service = activity_service

    def _active_org_id(self) -> str:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_organization_id(
            operation_label="calendar access",
        )

    def list_calendars(
        self,
        *,
        calendar_type: str | None = None,
        active_only: bool | None = None,
    ) -> list[PlatformCalendar]:
        require_permission(self._user_session, "calendar.read", operation_label="list calendars")
        org_id = self._active_org_id()
        return self._calendar_repo.list_for_organization(
            org_id, calendar_type=calendar_type, active_only=active_only
        )

    def get_calendar(self, calendar_id: str) -> PlatformCalendar:
        require_permission(self._user_session, "calendar.read", operation_label="get calendar")
        return self._require_calendar_in_active_organization(calendar_id)

    def get_calendars_by_ids(
        self, calendar_ids: Iterable[str]
    ) -> dict[str, PlatformCalendar]:
        """Batch calendar lookup, scoped to the active organization.

        Serving one map lookup per assignment (instead of one
        get_calendar() call per assignment) is what keeps assignment-list
        serialization at a constant query count regardless of how many
        assignments are returned.
        """
        require_permission(self._user_session, "calendar.read", operation_label="get calendars")
        ids = set(calendar_ids)
        if not ids:
            return {}
        calendars = self._calendar_repo.list_by_ids(ids)
        return {cal.id: cal for cal in calendars}

    def get_default_calendar(self) -> PlatformCalendar:
        require_permission(
            self._user_session,
            "calendar.read",
            operation_label="get default calendar",
        )
        org_id = self._active_org_id()
        calendar = self._calendar_repo.get_global(org_id)
        if calendar is None:
            raise NotFoundError(
                "The active organization has no default global calendar.",
                code="DEFAULT_CALENDAR_NOT_FOUND",
            )
        return calendar

    def create_calendar(
        self,
        *,
        code: str,
        name: str,
        calendar_type: str,
        timezone: str = "UTC",
        description: str | None = None,
        base_calendar_id: str | None = None,
        scope_type: str | None = None,
        scope_id: str | None = None,
        locale: str | None = None,
        is_default: bool = False,
        effective_from: date | None = None,
        effective_to: date | None = None,
        priority: int = 0,
    ) -> PlatformCalendar:
        require_permission(
            self._user_session, "calendar.manage", operation_label="create calendar"
        )
        org_id = self._active_org_id()
        username = _resolve_username(self._user_session)
        cal = PlatformCalendar.create(
            organization_id=org_id,
            code=code,
            name=name,
            calendar_type=calendar_type,
            timezone=timezone,
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
        existing = self._calendar_repo.get_by_code(org_id, cal.code)
        if existing is not None:
            raise ValidationError(f"Calendar code '{cal.code}' already exists.")
        self._calendar_repo.add(cal)
        if is_default:
            # The organization invariant is "exactly one effective default
            # calendar" -- unmark any other calendar currently marked
            # default rather than letting a second one coexist.
            self._unmark_other_defaults(org_id, keep_calendar_id=cal.id, username=username)
        record_activity(
            self,
            action="calendar.create",
            entity_type="calendar",
            entity_id=cal.id,
            module="platform",
            organization_id=org_id,
            message=f"Calendar created — {cal.name}",
            icon="calendar",
            commit=False,
        )
        self._session.commit()
        return cal

    def update_calendar(
        self,
        calendar_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        timezone: str | None = None,
        locale: str | None = None,
        is_active: bool | None = None,
        effective_from: date | None = None,
        effective_to: date | None = None,
        priority: int | None = None,
    ) -> PlatformCalendar:
        """Profile fields only -- `is_default` is never settable through this
        generic update. Changing which calendar is the organization's
        default is an explicit, atomic operation (see
        set_organization_default_calendar) because it must unmark the
        previous default in the same transaction; a free-standing boolean
        field on a generic update could otherwise leave an organization with
        zero or two defaults."""
        require_permission(
            self._user_session, "calendar.manage", operation_label="update calendar"
        )
        cal = self._require_calendar_in_active_organization(calendar_id)
        if is_active is False and cal.is_default:
            raise BusinessRuleError(
                f"Cannot deactivate '{cal.name}': it is the organization's default "
                "calendar. Set a different calendar as the default first.",
                code="CALENDAR_DEFAULT_CANNOT_DEACTIVATE",
            )
        username = _resolve_username(self._user_session)
        updated = replace(
            cal,
            name=cal.name if name is None else name,
            description=cal.description if description is None else description,
            timezone=cal.timezone if timezone is None else timezone,
            locale=cal.locale if locale is None else locale,
            is_active=cal.is_active if is_active is None else is_active,
            effective_from=cal.effective_from if effective_from is None else effective_from,
            effective_to=cal.effective_to if effective_to is None else effective_to,
            priority=cal.priority if priority is None else priority,
            version=cal.version + 1,
            updated_at=datetime.now(zone.utc),
            updated_by=username,
        )
        self._calendar_repo.update(updated)
        record_activity(
            self,
            action="calendar.update",
            entity_type="calendar",
            entity_id=updated.id,
            module="platform",
            organization_id=updated.organization_id,
            message=f"Calendar updated — {updated.name}",
            icon="calendar",
            commit=False,
        )
        self._session.commit()
        return updated

    def set_organization_default_calendar(self, calendar_id: str) -> PlatformCalendar:
        """Explicit, atomic operation for changing which calendar is the
        organization's default -- requires both calendar authority and
        organization-management authority, since this affects every Site/
        Department/Employee that falls back to the organization level.
        Unmarks the previous default (if any, and if different) in the same
        transaction; the old calendar then follows normal lifecycle rules
        (it is no longer protected from deactivation/deletion once it is no
        longer the default)."""
        require_permission(
            self._user_session, "calendar.manage", operation_label="set organization default calendar"
        )
        require_permission(
            self._user_session, "org.manage", operation_label="set organization default calendar"
        )
        org_id = self._active_org_id()
        new_default = self._require_calendar_in_active_organization(calendar_id)
        if not new_default.is_active:
            raise ValidationError(
                f"Calendar '{new_default.name}' is not active.", code="CALENDAR_INACTIVE"
            )
        if new_default.is_default:
            return new_default
        username = _resolve_username(self._user_session)
        now = datetime.now(zone.utc)
        self._unmark_other_defaults(org_id, keep_calendar_id=calendar_id, username=username, now=now)
        updated = replace(
            new_default,
            is_default=True,
            version=new_default.version + 1,
            updated_at=now,
            updated_by=username,
        )
        self._calendar_repo.update(updated)
        record_activity(
            self,
            action="calendar.set_organization_default",
            entity_type="calendar",
            entity_id=updated.id,
            module="platform",
            organization_id=org_id,
            message=f"Organization default calendar changed to {updated.name}",
            icon="calendar",
            commit=False,
        )
        self._session.commit()
        return updated

    def _unmark_other_defaults(
        self,
        organization_id: str,
        *,
        keep_calendar_id: str,
        username: str | None,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(zone.utc)
        for cal in self._calendar_repo.list_for_organization(organization_id):
            if cal.is_default and cal.id != keep_calendar_id:
                self._calendar_repo.update(
                    replace(
                        cal,
                        is_default=False,
                        version=cal.version + 1,
                        updated_at=now,
                        updated_by=username,
                    )
                )

    def delete_calendar(self, calendar_id: str) -> None:
        require_permission(
            self._user_session, "calendar.manage", operation_label="delete calendar"
        )
        cal = self._require_calendar_in_active_organization(calendar_id)

        if cal.is_default:
            raise BusinessRuleError(
                f"Cannot delete '{cal.name}': it is the organization's default calendar. "
                "Set a different calendar as the default first.",
                code="CALENDAR_DEFAULT_CANNOT_DELETE",
            )
        count = self._assignment_repo.count_active_assignments_for_calendar(calendar_id)
        if count > 0:
            raise BusinessRuleError(
                f"Cannot delete calendar '{cal.name}': it is assigned to {count} "
                "site(s), department(s), or employee(s). Remove assignments first."
            )
        self._calendar_repo.delete(calendar_id)
        # Recorded before delete() commits -- the calendar row is gone after
        # this transaction, but the activity row (keyed by the now-deleted
        # calendar_id) still lets a cross-entity activity view explain what
        # happened to it.
        record_activity(
            self,
            action="calendar.delete",
            entity_type="calendar",
            entity_id=cal.id,
            module="platform",
            organization_id=cal.organization_id,
            message=f"Calendar deleted — {cal.name}",
            icon="calendar",
            type="warning",
            commit=False,
        )
        self._session.commit()

    def ensure_global_calendar(self, organization_id: str) -> PlatformCalendar:
        """Bootstrap: create the organization's default (GLOBAL) calendar if
        it doesn't already exist, seeding Mon-Fri working rules."""
        existing = self._calendar_repo.get_global(organization_id)
        if existing is not None:
            self._ensure_working_rules(existing.id)
            self._session.commit()
            return existing

        # The calendar's own working-time interpretation is local to its
        # configured timezone, not UTC -- prefer the organization's own
        # configured timezone (same as OrganizationService's own
        # _add_default_calendar_rows, which creates this same shape of
        # calendar transactionally at organization-creation time; this path
        # only runs for organizations that predate that invariant).
        organization = self._organization_repo.get(organization_id) if self._organization_repo else None
        calendar_timezone = getattr(organization, "timezone_name", None) or "UTC"

        now = datetime.now(zone.utc)
        cal = PlatformCalendar(
            id=f"global-{organization_id[:8]}",
            organization_id=organization_id,
            code="GLOBAL",
            name="Global Calendar",
            calendar_type=CalendarType.GLOBAL.value,
            timezone=calendar_timezone,
            description="Organization-wide default working calendar.",
            is_default=True,
            is_active=True,
            priority=0,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._calendar_repo.add(cal)
        self._session.flush()
        self._seed_default_working_rules(cal.id)

        self._session.commit()
        return cal

    def _ensure_working_rules(self, calendar_id: str) -> None:
        if self._rule_repo is None:
            logger.warning(
                "Cannot verify global calendar working rules because rule repository is unavailable calendar_id=%s",
                calendar_id,
            )
            return
        existing_rules = self._rule_repo.list_for_calendar(calendar_id)
        if existing_rules:
            return
        logger.warning(
            "Global calendar has no working rules; seeding default working week calendar_id=%s",
            calendar_id,
        )
        self._seed_default_working_rules(calendar_id)

    def _seed_default_working_rules(self, calendar_id: str) -> None:
        """Seeds Mon-Fri 08:00-17:00 (60-minute break, 8 net hours) working
        rules. Safe to call multiple times -- skips if rules already exist."""
        from datetime import time

        from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
            CalendarWorkingRule,
        )

        if self._rule_repo is None:
            logger.warning(
                "Skipping default working rule seed because rule repository is unavailable calendar_id=%s",
                calendar_id,
            )
            return

        try:
            existing_rules = self._rule_repo.list_for_calendar(calendar_id)
            if existing_rules:
                return
            working_days = {0, 1, 2, 3, 4}
            hours = 8.0
            break_minutes = 60
            # The start/end window must be consistent with net hours + break
            # -- e.g. 08:00 start, 8 net hours, 60-min break means the window
            # itself spans 9 hours (08:00-17:00), not 8 (08:00-16:00, which
            # compute_hours() would silently read as only 7 net hours the
            # moment hours_override is ever cleared).
            start_total_minutes = 8 * 60
            end_total_minutes = start_total_minutes + int(round(hours * 60)) + break_minutes
            end_hour = min(end_total_minutes // 60, 23)
            end_minute = end_total_minutes % 60
            for weekday in range(7):
                is_working = weekday in working_days
                rule = CalendarWorkingRule.create(
                    calendar_id=calendar_id,
                    weekday=weekday,
                    is_working_day=is_working,
                    start_time=time(8, 0) if is_working else None,
                    end_time=time(end_hour, end_minute) if is_working else None,
                    break_minutes=break_minutes if is_working else 0,
                    hours_override=hours if is_working else None,
                )
                self._rule_repo.save(rule)
        except Exception:
            logger.exception(
                "Failed to seed default working rules calendar_id=%s",
                calendar_id,
            )
            raise

    def _require_calendar_in_active_organization(self, calendar_id: str) -> PlatformCalendar:
        org_id = self._active_org_id()
        cal = self._calendar_repo.get(calendar_id)
        if cal is None or cal.organization_id != org_id:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")
        return cal


__all__ = ["PlatformCalendarService"]
