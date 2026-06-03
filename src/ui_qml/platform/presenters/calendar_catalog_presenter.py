from __future__ import annotations

from datetime import date
from typing import Any

from src.api.desktop.platform import (
    DesktopApiError,
    DesktopApiResult,
    PlatformCalendarDesktopApi,
    WorkingCalendarHolidayCreateCommand,
    WorkingCalendarSnapshotDto,
    WorkingCalendarUpdateCommand,
    WorkingDayCalculationCommand,
    WorkingDayCalculationDto,
)
from src.ui_qml.platform.presenters.support import int_value, preview_error_result, string_value
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


class PlatformCalendarCatalogPresenter:
    def __init__(
        self,
        *,
        calendar_api: PlatformCalendarDesktopApi | None = None,
        enterprise_calendar_api=None,
    ) -> None:
        self._calendar_api = calendar_api
        self._enterprise_calendar_api = enterprise_calendar_api

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        # Enterprise calendars take priority when available — they are the authoritative source.
        if self._enterprise_calendar_api is not None:
            return self._build_enterprise_catalog()

        if self._calendar_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Calendars",
                subtitle="Shared working calendars appear here once the Platform calendar API is connected.",
                empty_state="Platform calendar API is not connected in this QML preview.",
            )

        snapshot_result = self._calendar_api.get_calendar_snapshot()
        if not snapshot_result.ok or snapshot_result.data is None:
            message = (
                snapshot_result.error.message
                if snapshot_result.error is not None
                else "Unable to load shared working calendars."
            )
            return PlatformWorkspaceActionListViewModel(
                title="Calendars",
                subtitle=message,
                empty_state=message,
            )

        snapshot = snapshot_result.data
        return PlatformWorkspaceActionListViewModel(
            title="Calendars",
            subtitle="Shared working-calendar rules owned by Platform and consumed across modules.",
            empty_state="No shared working calendars are configured.",
            items=(self._serialize_calendar(snapshot),),
        )

    def _build_enterprise_catalog(self) -> PlatformWorkspaceActionListViewModel:
        result = self._enterprise_calendar_api.list_calendars()
        if not result.ok or result.data is None:
            message = (
                result.error.message
                if result.error is not None
                else "Unable to load enterprise calendars."
            )
            return PlatformWorkspaceActionListViewModel(
                title="Calendars",
                subtitle=message,
                empty_state=message,
            )
        calendars = result.data
        items = tuple(self._serialize_enterprise_calendar(cal) for cal in calendars)
        return PlatformWorkspaceActionListViewModel(
            title="Calendars",
            subtitle=f"Enterprise calendars — {len(items)} calendar(s) across all types. Owned by Platform.",
            empty_state="No enterprise calendars configured. Create a Global calendar to get started.",
            items=items,
        )

    def _serialize_enterprise_calendar(self, cal) -> PlatformWorkspaceActionItemViewModel:
        from src.ui_qml.platform.view_models import PlatformWorkspaceActionItemViewModel
        return PlatformWorkspaceActionItemViewModel(
            id=cal.id,
            title=cal.name,
            status_label=cal.calendar_type,
            subtitle=f"{cal.code} | {cal.timezone}",
            supporting_text=f"Type: {cal.calendar_type} | Default: {'Yes' if cal.is_default else 'No'}",
            meta_text=f"Active: {'Yes' if cal.is_active else 'No'}",
            can_primary_action=True,
            can_secondary_action=False,
            state={
                "calendarId": cal.id,
                "code": cal.code,
                "name": cal.name,
                "calendarType": cal.calendar_type,
                "timezone": cal.timezone,
                "isDefault": cal.is_default,
                "isActive": cal.is_active,
                "effectiveFrom": cal.effective_from,
                "effectiveTo": cal.effective_to,
                "isEnterpriseCalendar": True,
            },
        )

    def update_calendar(self, payload: dict[str, Any]) -> DesktopApiResult[WorkingCalendarSnapshotDto]:
        if self._calendar_api is None:
            return preview_error_result("Platform calendar API is not connected in this QML preview.")
        working_days = self._coerce_working_days(payload)
        if not working_days:
            return self._validation_error("Select at least one working day.")
        hours_text = string_value(payload, "hoursPerDay")
        try:
            hours_per_day = float(hours_text)
        except ValueError:
            return self._validation_error("Hours per day must be a valid number.")
        if hours_per_day <= 0:
            return self._validation_error("Hours per day must be greater than zero.")
        return self._calendar_api.update_calendar(
            WorkingCalendarUpdateCommand(
                working_days=tuple(sorted(set(working_days))),
                hours_per_day=hours_per_day,
            )
        )

    def add_holiday(
        self,
        payload: dict[str, Any],
    ) -> DesktopApiResult[object]:
        if self._calendar_api is None:
            return preview_error_result("Platform calendar API is not connected in this QML preview.")
        holiday_date = self._parse_iso_date(string_value(payload, "holidayDate"))
        if holiday_date is None:
            return self._validation_error("Holiday date must use YYYY-MM-DD.")
        return self._calendar_api.add_holiday(
            WorkingCalendarHolidayCreateCommand(
                holiday_date=holiday_date,
                name=string_value(payload, "name"),
            )
        )

    def delete_holiday(self, holiday_id: str) -> DesktopApiResult[None]:
        if self._calendar_api is None:
            return preview_error_result("Platform calendar API is not connected in this QML preview.")
        if not str(holiday_id or "").strip():
            return self._validation_error("Select a holiday exception to delete.")
        return self._calendar_api.delete_holiday(str(holiday_id).strip())

    def calculate_working_day(
        self,
        payload: dict[str, Any],
    ) -> DesktopApiResult[WorkingDayCalculationDto]:
        if self._calendar_api is None:
            return preview_error_result("Platform calendar API is not connected in this QML preview.")
        start_date = self._parse_iso_date(string_value(payload, "startDate"))
        if start_date is None:
            return self._validation_error("Start date must use YYYY-MM-DD.")
        working_days = int_value(payload, "workingDays")
        if working_days is None or working_days < 0:
            return self._validation_error("Working days must be zero or greater.")
        return self._calendar_api.calculate_working_day(
            WorkingDayCalculationCommand(
                start_date=start_date,
                working_days=working_days,
            )
        )

    @staticmethod
    def format_calculation_result(result: WorkingDayCalculationDto) -> str:
        skipped = int(getattr(result, "skipped_non_working_days", 0) or 0)
        skipped_text = "1 non-working day skipped" if skipped == 1 else f"{skipped} non-working days skipped"
        return (
            f"{result.working_days} working day(s) from {result.start_date.isoformat()} "
            f"lands on {result.result_date.isoformat()} ({skipped_text})."
        )

    def _serialize_calendar(
        self,
        snapshot: WorkingCalendarSnapshotDto,
    ) -> PlatformWorkspaceActionItemViewModel:
        working_days = [day.label for day in snapshot.working_days if day.checked]
        working_days_text = ", ".join(working_days) or "No working days"
        holiday_rows = [
            {
                "id": holiday.id,
                "date": holiday.date.isoformat(),
                "name": holiday.name or "Non-working day",
                "calendar": snapshot.name,
                "details": "Shared calendar exception",
            }
            for holiday in snapshot.holidays
        ]
        hours_label = f"{float(snapshot.hours_per_day):g}"
        return PlatformWorkspaceActionItemViewModel(
            id=snapshot.id,
            title=snapshot.name,
            status_label="Shared",
            subtitle=f"{working_days_text} | {hours_label}h/day",
            supporting_text=f"{len(snapshot.holidays)} holiday exception(s) registered across the shared runtime calendar.",
            meta_text="Platform-owned shared working calendar",
            can_primary_action=True,
            can_secondary_action=False,
            state={
                "calendarId": snapshot.id,
                "name": snapshot.name,
                "hoursPerDay": snapshot.hours_per_day,
                "hoursPerDayLabel": hours_label,
                "workingDays": [
                    {
                        "index": day.index,
                        "label": day.label,
                        "checked": day.checked,
                    }
                    for day in snapshot.working_days
                ],
                "workingDaysText": working_days_text,
                "holidayCount": len(snapshot.holidays),
                "summaryText": f"{working_days_text} | {hours_label}h/day",
                "holidays": holiday_rows,
            },
        )

    @staticmethod
    def _coerce_working_days(payload: dict[str, Any]) -> list[int]:
        raw_days = payload.get("workingDays")
        if not isinstance(raw_days, (list, tuple)):
            return []
        resolved: list[int] = []
        for value in raw_days:
            try:
                index = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= index <= 6:
                resolved.append(index)
        return resolved

    @staticmethod
    def _parse_iso_date(raw: str) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    @staticmethod
    def _validation_error(message: str) -> DesktopApiResult[object]:
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code="validation_error",
                message=message,
                category="validation",
            ),
        )


__all__ = ["PlatformCalendarCatalogPresenter"]
