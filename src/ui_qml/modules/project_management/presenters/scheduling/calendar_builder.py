from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingCalendarViewModel,
    SchedulingDayOptionViewModel,
    SchedulingRecordViewModel,
)


def build_calendar_view_model(calendar_snapshot) -> SchedulingCalendarViewModel:
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
                "calendar": "Default Calendar",
                "workingDays": "",
                "shiftPattern": "Holiday",
                "hoursPerDay": "-",
                "exceptions": holiday.name or "Non-working day",
            },
        )
        for holiday in calendar_snapshot.holidays
    )
    active_days = [day.label for day in calendar_snapshot.working_days if day.checked]
    summary = (
        f"Working days: {', '.join(active_days) or 'none'} | "
        f"{float(calendar_snapshot.hours_per_day or 0.0):g} hours per day | "
        f"{len(calendar_snapshot.holidays)} holiday(s)"
    )
    return SchedulingCalendarViewModel(
        summary_text=summary,
        working_day_options=tuple(
            SchedulingDayOptionViewModel(
                index=day.index,
                label=day.label,
                checked=day.checked,
            )
            for day in calendar_snapshot.working_days
        ),
        hours_per_day=f"{float(calendar_snapshot.hours_per_day or 0.0):g}",
        holidays=holidays,
        empty_state="No non-working day exceptions have been configured yet.",
    )


__all__ = ["build_calendar_view_model"]
