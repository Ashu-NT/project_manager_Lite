"""Calendar platform calendar operations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
)
from src.core.platform.contract.repositories.time_management.calendar.contracts import (
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    PlatformCalendar,
)


class PlatformCalendarQueryHandler:
    """Read-only lookups for platform calendar."""

    def __init__(
        self,
        *,
        calendar_repo: PlatformCalendarRepository,
        user_session: Any = None,
        tenant_context_service: TenantContextService | None = None,
    ) -> None:
        self._calendar_repo = calendar_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

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
        require_permission(
            self._user_session, "calendar.read", operation_label="list calendars"
        )
        org_id = self._active_org_id()
        return self._calendar_repo.list_for_organization(
            org_id, calendar_type=calendar_type, active_only=active_only
        )

    def get_calendar(self, calendar_id: str) -> PlatformCalendar:
        require_permission(
            self._user_session, "calendar.read", operation_label="get calendar"
        )
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
        require_permission(
            self._user_session, "calendar.read", operation_label="get calendars"
        )
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

    def _require_calendar_in_active_organization(
        self, calendar_id: str
    ) -> PlatformCalendar:
        org_id = self._active_org_id()
        cal = self._calendar_repo.get(calendar_id)
        if cal is None or cal.organization_id != org_id:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")
        return cal


__all__ = ["PlatformCalendarQueryHandler"]
