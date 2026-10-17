"""Platform calendar integration helpers."""

from __future__ import annotations

from typing import ClassVar

from src.core.modules.project_management.application.scheduling.dto.responses.calendars import (
    SchedulingCalendarSnapshot,
)
from src.core.modules.project_management.application.scheduling.mappers.calendars import (
    map_platform_calendar_snapshot,
)
from src.core.platform.api.desktop.time_management.calendar.models.platform_calendar import (
    CalendarDto,
)


class _DefaultCalendar:
    id = "default"
    name = "Global Calendar"
    working_days : ClassVar[set[int]] = {0, 1, 2, 3, 4}
    hours_per_day = 8.0


def get_legacy_calendar(work_calendar_service=None):
    if work_calendar_service is not None:
        return work_calendar_service.get_calendar()
    return _DefaultCalendar()


def list_legacy_holidays(work_calendar_service=None) -> list:
    if work_calendar_service is None:
        return []
    return work_calendar_service.list_holidays()


def unwrap_platform_calendar_result(result):
    if bool(getattr(result, "ok", False)):
        return getattr(result, "data", None)
    error = getattr(result, "error", None)
    category = str(getattr(error, "category", "") or "").strip().lower()
    message = str(getattr(error, "message", "") or "Platform calendar operation failed.")
    if category == "validation":
        raise ValueError(message)
    if category == "permission":
        raise PermissionError(message)
    if message:
        raise RuntimeError(message)
    raise RuntimeError("Platform calendar operation failed.")


def _resolve_calendar_id(platform_calendar_api, calendar_id: str) -> str:
    # "default" is the QML view model's fallback sentinel (never a real
    # platform calendar id) — treat it the same as "no id supplied".
    if calendar_id and calendar_id != "default":
        return calendar_id
    default_calendar = unwrap_platform_calendar_result(
        platform_calendar_api.get_default_calendar()
    )
    return default_calendar.id


def list_platform_calendar_options(
    platform_calendar_api,
) -> tuple[CalendarDto, ...]:
    calendars = unwrap_platform_calendar_result(platform_calendar_api.list_calendars()) or ()
    return tuple(calendars)


def get_platform_calendar_snapshot(
    platform_calendar_api, calendar_id: str = ""
) -> SchedulingCalendarSnapshot:
    resolved_id = _resolve_calendar_id(platform_calendar_api, calendar_id)
    cal = unwrap_platform_calendar_result(platform_calendar_api.get_calendar(resolved_id))
    rules = unwrap_platform_calendar_result(
        platform_calendar_api.list_working_rules(resolved_id)
    ) or ()
    exceptions = unwrap_platform_calendar_result(
        platform_calendar_api.list_exceptions(resolved_id)
    ) or ()

    return map_platform_calendar_snapshot(cal, rules, exceptions)


__all__ = [
    "get_legacy_calendar",
    "get_platform_calendar_snapshot",
    "list_legacy_holidays",
    "list_platform_calendar_options",
    "unwrap_platform_calendar_result",
]
