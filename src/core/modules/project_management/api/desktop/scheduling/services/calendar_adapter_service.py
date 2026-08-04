"""Platform calendar integration helpers."""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.scheduling.models.calendars import (
    _DAY_LABELS,
    SchedulingCalendarOptionDescriptor,
    SchedulingCalendarSnapshotDto,
    SchedulingDayDescriptor,
    SchedulingHolidayDto,
)


class _DefaultCalendar:
    id = "default"
    name = "Global Calendar"
    working_days = {0, 1, 2, 3, 4}
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


def _default_platform_calendar_id(platform_calendar_api) -> str:
    global_calendars = unwrap_platform_calendar_result(
        platform_calendar_api.list_calendars(calendar_type="GLOBAL")
    ) or ()
    if global_calendars:
        return global_calendars[0].id
    any_calendars = unwrap_platform_calendar_result(platform_calendar_api.list_calendars()) or ()
    return any_calendars[0].id if any_calendars else ""


def _resolve_calendar_id(platform_calendar_api, calendar_id: str) -> str:
    # "default" is the QML view model's fallback sentinel (never a real
    # platform calendar id) — treat it the same as "no id supplied".
    if calendar_id and calendar_id != "default":
        return calendar_id
    return _default_platform_calendar_id(platform_calendar_api)


def list_platform_calendar_options(
    platform_calendar_api,
) -> tuple[SchedulingCalendarOptionDescriptor, ...]:
    calendars = unwrap_platform_calendar_result(platform_calendar_api.list_calendars()) or ()
    return tuple(
        SchedulingCalendarOptionDescriptor(
            value=cal.id,
            label=cal.name,
            summary_label=f"{cal.calendar_type.title()} · {cal.timezone}",
        )
        for cal in calendars
    )


def get_platform_calendar_snapshot(
    platform_calendar_api, calendar_id: str = ""
) -> SchedulingCalendarSnapshotDto:
    resolved_id = _resolve_calendar_id(platform_calendar_api, calendar_id)
    cal = unwrap_platform_calendar_result(platform_calendar_api.get_calendar(resolved_id))
    rules = unwrap_platform_calendar_result(
        platform_calendar_api.list_working_rules(resolved_id)
    ) or ()
    exceptions = unwrap_platform_calendar_result(
        platform_calendar_api.list_exceptions(resolved_id)
    ) or ()

    rules_by_weekday = {rule.weekday: rule for rule in rules}
    working_days = tuple(
        SchedulingDayDescriptor(
            index=i,
            label=_DAY_LABELS[i],
            checked=bool(rules_by_weekday[i].is_working_day) if i in rules_by_weekday else False,
        )
        for i in range(7)
    )
    working_hours = [
        rule.computed_hours
        for rule in rules
        if rule.is_working_day and rule.computed_hours
    ]
    hours_per_day = working_hours[0] if working_hours else 8.0

    holidays = tuple(
        sorted(
            (
                SchedulingHolidayDto(
                    id=exc.id,
                    date=date.fromisoformat(exc.exception_date),
                    name=exc.name or "",
                )
                for exc in exceptions
                if str(exc.exception_type or "").upper() == "HOLIDAY" and exc.exception_date
            ),
            key=lambda item: item.date,
        )
    )

    return SchedulingCalendarSnapshotDto(
        calendar_id=cal.id,
        calendar_name=cal.name,
        working_days=working_days,
        hours_per_day=float(hours_per_day),
        holidays=holidays,
    )


def update_platform_calendar_working_days(
    platform_calendar_api, calendar_id: str, command
) -> SchedulingCalendarSnapshotDto:
    from src.core.platform.api.desktop.time_management.calendar.models.enterprise_calendar import WorkingRuleSaveCommand

    resolved_id = _resolve_calendar_id(platform_calendar_api, calendar_id)
    working_days = set(command.working_days or ())
    for weekday in range(7):
        is_working_day = weekday in working_days
        platform_calendar_api.save_working_rule(
            WorkingRuleSaveCommand(
                calendar_id=resolved_id,
                weekday=weekday,
                is_working_day=is_working_day,
                hours_override=command.hours_per_day if is_working_day else 0.0,
            )
        )
    return get_platform_calendar_snapshot(platform_calendar_api, resolved_id)


def add_platform_holiday(
    platform_calendar_api, calendar_id: str, command
) -> SchedulingHolidayDto:
    from src.core.platform.api.desktop.time_management.calendar.models.enterprise_calendar import ExceptionCreateCommand

    resolved_id = _resolve_calendar_id(platform_calendar_api, calendar_id)
    exc = unwrap_platform_calendar_result(
        platform_calendar_api.add_exception(
            ExceptionCreateCommand(
                calendar_id=resolved_id,
                exception_date=command.holiday_date.isoformat(),
                exception_type="HOLIDAY",
                name=command.name or "",
                impact_type="UNAVAILABLE",
            )
        )
    )
    return SchedulingHolidayDto(
        id=exc.id,
        date=date.fromisoformat(exc.exception_date),
        name=exc.name or "",
    )


def delete_platform_holiday(platform_calendar_api, holiday_id: str) -> None:
    if not holiday_id:
        return
    unwrap_platform_calendar_result(platform_calendar_api.delete_exception(holiday_id))


__all__ = [
    "add_platform_holiday",
    "delete_platform_holiday",
    "get_legacy_calendar",
    "get_platform_calendar_snapshot",
    "list_legacy_holidays",
    "list_platform_calendar_options",
    "unwrap_platform_calendar_result",
    "update_platform_calendar_working_days",
]
