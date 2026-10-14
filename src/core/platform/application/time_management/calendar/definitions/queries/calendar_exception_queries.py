"""Calendar calendar exception operations."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.repositories.time_management.calendar.contracts import (
    CalendarExceptionRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarException,
)


class CalendarExceptionQueryHandler:
    """Read-only lookups for calendar exception."""

    def __init__(
        self,
        *,
        calendar_repo: PlatformCalendarRepository,
        exception_repo: CalendarExceptionRepository,
        user_session: Any = None,
    ) -> None:
        self._calendar_repo = calendar_repo
        self._exception_repo = exception_repo
        self._user_session = user_session

    def list_exceptions(
        self,
        calendar_id: str,
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> list[CalendarException]:
        require_permission(
            self._user_session, "calendar.read", operation_label="list exceptions"
        )
        self._require_calendar(calendar_id)
        return self._exception_repo.list_for_calendar(calendar_id, start=start, end=end)

    def _require_calendar(self, calendar_id: str) -> None:
        if self._calendar_repo.get(calendar_id) is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")


__all__ = ["CalendarExceptionQueryHandler"]
