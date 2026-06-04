"""Calendar snapshot and options assembly."""

from src.core.modules.project_management.api.desktop.scheduling.models.calendars import (
    _DAY_LABELS,
    SchedulingCalendarOptionDescriptor,
    SchedulingCalendarSnapshotDto,
    SchedulingDayDescriptor,
    SchedulingHolidayDto,
)
from src.core.modules.project_management.api.desktop.scheduling.services.calendar_adapter_service import (
    get_legacy_calendar,
    list_legacy_holidays,
    unwrap_platform_calendar_result,
)


def build_calendar_options(
    platform_calendar_api=None,
    work_calendar_service=None,
) -> tuple[SchedulingCalendarOptionDescriptor, ...]:
    if platform_calendar_api is not None:
        options = unwrap_platform_calendar_result(platform_calendar_api.list_calendars()) or ()
        return tuple(
            SchedulingCalendarOptionDescriptor(
                value=o.value, label=o.label, summary_label=o.summary_label,
            )
            for o in options
        )
    calendar = get_legacy_calendar(work_calendar_service)
    working_days = set(calendar.working_days or {0, 1, 2, 3, 4})
    active_labels = [_DAY_LABELS[i] for i in range(7) if i in working_days]
    return (
        SchedulingCalendarOptionDescriptor(
            value=str(getattr(calendar, "id", "") or "default"),
            label=str(getattr(calendar, "name", "") or "Default Calendar").strip(),
            summary_label=(
                f"{', '.join(active_labels) or 'No days'} | "
                f"{float(calendar.hours_per_day or 8.0):g}h/day"
            ),
        ),
    )


def build_calendar_snapshot(
    platform_calendar_api=None,
    work_calendar_service=None,
) -> SchedulingCalendarSnapshotDto:
    if platform_calendar_api is not None:
        snapshot = unwrap_platform_calendar_result(platform_calendar_api.get_calendar_snapshot())
        return SchedulingCalendarSnapshotDto(
            working_days=tuple(
                SchedulingDayDescriptor(index=d.index, label=d.label, checked=d.checked)
                for d in snapshot.working_days
            ),
            hours_per_day=float(snapshot.hours_per_day or 8.0),
            holidays=tuple(
                SchedulingHolidayDto(id=h.id, date=h.date, name=h.name or "")
                for h in snapshot.holidays
            ),
        )
    calendar = get_legacy_calendar(work_calendar_service)
    holidays = list_legacy_holidays(work_calendar_service)
    working_days = set(calendar.working_days or {0, 1, 2, 3, 4})
    return SchedulingCalendarSnapshotDto(
        working_days=tuple(
            SchedulingDayDescriptor(index=i, label=_DAY_LABELS[i], checked=i in working_days)
            for i in range(7)
        ),
        hours_per_day=float(calendar.hours_per_day or 8.0),
        holidays=tuple(
            SchedulingHolidayDto(id=h.id, date=h.date, name=h.name or "")
            for h in sorted(holidays, key=lambda item: item.date)
        ),
    )


__all__ = ["build_calendar_options", "build_calendar_snapshot"]
