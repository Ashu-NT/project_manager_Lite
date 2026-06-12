from __future__ import annotations

from typing import Any

from src.api.desktop.platform import (
    DesktopApiResult,
    WorkingDayCalculationCommand,
    WorkingDayCalculationDto,
)
from src.ui_qml.platform.presenters.support import int_value, preview_error_result, string_value
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)

class PlatformCalendarCatalogPresenter:
    """
    Builds the calendar catalog for the admin console.

    When enterprise_calendar_api is available (always in production),
    it lists all enterprise platform_calendars.

    The legacy calendar_api parameter is unused — PlatformCalendarDesktopApi was removed.
    """

    def __init__(
        self,
        *,
        calendar_api=None,  # removed — kept for signature compat during transition
        enterprise_calendar_api=None,
    ) -> None:
        self._enterprise_calendar_api = enterprise_calendar_api

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        if self._enterprise_calendar_api is not None:
            return self._build_enterprise_catalog()
        return PlatformWorkspaceActionListViewModel(
            title="Calendars",
            subtitle="Enterprise calendar API is not connected.",
            empty_state="No calendars available.",
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
            subtitle=f"Enterprise calendars — {len(items)} calendar(s). Owned by Platform.",
            empty_state="No enterprise calendars configured. A Global calendar is created automatically at startup.",
            items=items,
        )

    def _serialize_enterprise_calendar(self, cal) -> PlatformWorkspaceActionItemViewModel:
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

    def calculate_working_day(
        self,
        payload: dict[str, Any],
    ) -> DesktopApiResult[WorkingDayCalculationDto]:
        """Working-day calculator — uses enterprise resolver via the API."""
        if self._enterprise_calendar_api is None:
            return preview_error_result("Enterprise calendar API is not connected.")
        start_date_str = string_value(payload, "startDate")
        if not start_date_str:
            from src.api.desktop.platform import DesktopApiError
            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(code="validation", message="Start date is required.", category="validation"),
            )
        working_days = int_value(payload, "workingDays")
        if working_days is None or working_days < 0:
            from src.api.desktop.platform import DesktopApiError
            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(code="validation", message="Working days must be >= 0.", category="validation"),
            )
        from src.api.desktop.platform.models.enterprise_calendar import WorkingDaysCommand
        return self._enterprise_calendar_api.calculate_working_days(
            WorkingDaysCommand(start_date=start_date_str, working_days=working_days)
        )

    @staticmethod
    def format_calculation_result(result) -> str:
        if result is None:
            return "Calculation unavailable."
        end_date = getattr(result, "end_date", None) or getattr(result, "result_date", None)
        working_days = getattr(result, "working_days", "?")
        start = getattr(result, "start_date", "?")
        return f"{working_days} working day(s) from {start} lands on {end_date}."

__all__ = ["PlatformCalendarCatalogPresenter"]
