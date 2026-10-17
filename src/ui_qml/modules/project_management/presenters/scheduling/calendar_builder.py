from __future__ import annotations

from src.core.modules.project_management.application.scheduling.dto.responses.calendars import (
    SchedulingCalendarResponse,
    SchedulingCalendarSnapshot,
)
from src.core.platform.api.desktop.time_management.calendar.models.platform_calendar import (
    CalendarDto,
)
from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingCalendarViewModel,
    SchedulingDayOptionViewModel,
    SchedulingRecordViewModel,
    SchedulingSelectorOptionViewModel,
)

DAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def to_calendar_option(
    calendar: CalendarDto | SchedulingCalendarResponse,
) -> SchedulingSelectorOptionViewModel:
    if isinstance(calendar, SchedulingCalendarResponse):
        labels = [DAY_LABELS[i] for i in range(7) if i in calendar.working_days]
        summary = f"{', '.join(labels) or 'No days'} | {calendar.hours_per_day:g}h/day"
    else:
        summary = f"{calendar.calendar_type.title()} \u00b7 {calendar.timezone}"
    return SchedulingSelectorOptionViewModel(
        value=calendar.id, label=calendar.name, supporting_text=summary
    )


def build_calendar_view_model(
    calendar_snapshot: SchedulingCalendarSnapshot,
) -> SchedulingCalendarViewModel:
    calendar_name = str(
        calendar_snapshot.calendar_name or "Default Calendar"
    )
    holidays = tuple(
        SchedulingRecordViewModel(
            id=holiday.id,
            title=holiday.date.isoformat(),
            status_label="Holiday",
            subtitle=holiday.name or "Non-working day",
            supporting_text="Removed days are excluded from scheduling and working-day calculation.",
            meta_text="Exception",
            can_tertiary_action=True,
            state={
                "holidayId": holiday.id,
                "calendar": calendar_name,
                "workingDays": "",
                "shiftPattern": "Holiday",
                "hoursPerDay": "-",
                "exceptions": holiday.name or "Non-working day",
            },
        )
        for holiday in calendar_snapshot.holidays
    )
    active_days = [
        DAY_LABELS[i] for i in range(7) if i in calendar_snapshot.working_days
    ]
    summary = (
        f"Working days: {', '.join(active_days) or 'none'} | "
        f"{float(calendar_snapshot.hours_per_day or 0.0):g} hours per day | "
        f"{len(calendar_snapshot.holidays)} holiday(s)"
    )
    return SchedulingCalendarViewModel(
        summary_text=summary,
        working_day_options=tuple(
            SchedulingDayOptionViewModel(
                index=i,
                label=DAY_LABELS[i],
                checked=i in calendar_snapshot.working_days,
            )
            for i in range(7)
        ),
        hours_per_day=f"{float(calendar_snapshot.hours_per_day or 0.0):g}",
        holidays=holidays,
        empty_state="No non-working day exceptions have been configured yet.",
        calendar_id=calendar_snapshot.calendar_id,
        calendar_name=calendar_name,
    )


__all__ = ["build_calendar_view_model"]
