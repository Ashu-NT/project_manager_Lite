"""Calendar working rule operations."""

from __future__ import annotations

from typing import Any

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.repositories.time_management.calendar.contracts import (
    CalendarWorkingRuleRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarWorkingRule,
)


class WorkingRuleQueryHandler:
    """Read-only lookups for working rule."""

    def __init__(
        self,
        *,
        calendar_repo: PlatformCalendarRepository,
        rule_repo: CalendarWorkingRuleRepository,
        user_session: Any = None,
    ) -> None:
        self._calendar_repo = calendar_repo
        self._rule_repo = rule_repo
        self._user_session = user_session

    def list_rules(self, calendar_id: str) -> list[CalendarWorkingRule]:
        require_permission(
            self._user_session, "calendar.read", operation_label="list working rules"
        )
        self._require_calendar(calendar_id)
        return self._rule_repo.list_for_calendar(calendar_id)

    def _require_calendar(self, calendar_id: str) -> None:
        if self._calendar_repo.get(calendar_id) is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")


__all__ = ["WorkingRuleQueryHandler"]
