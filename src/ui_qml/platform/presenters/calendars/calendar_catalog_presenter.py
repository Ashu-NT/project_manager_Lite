from __future__ import annotations

from typing import Any

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.time_management.calendar.models.calendar import (
    WorkingDayCalculationDto,
)
from src.ui_qml.platform.presenters.common.calendar_summary_support import (
    working_week_label,
)
from src.ui_qml.platform.presenters.common.presenter_support_helpers import (
    int_value,
    preview_error_result,
    string_value,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)

_CALENDAR_TYPE_LABELS = {
    "GLOBAL": "Organization",
    "SITE": "Site",
    "DEPARTMENT": "Department",
    "EMPLOYEE": "Employee",
    "PROJECT": "Project",
    "RESOURCE": "Resource",
}


def _calendar_status_label(is_active: bool) -> dict[str, str]:
    return {"label": "Active", "tone": "success"} if is_active else {"label": "Inactive", "tone": "neutral"}


class PlatformCalendarCatalogPresenter:
    """Builds the calendar catalog for the admin console from
    PlatformCalendarDesktopApi."""

    def __init__(
        self,
        *,
        platform_calendar_api=None,
    ) -> None:
        self._platform_calendar_api = platform_calendar_api

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        if self._platform_calendar_api is not None:
            return self._build_calendar_catalog()
        return PlatformWorkspaceActionListViewModel(
            title="Calendars",
            subtitle="Calendar API is not connected.",
            empty_state="No calendars available.",
        )

    def _build_calendar_catalog(self) -> PlatformWorkspaceActionListViewModel:
        result = self._platform_calendar_api.list_calendars()
        if not result.ok or result.data is None:
            message = (
                result.error.message
                if result.error is not None
                else "Unable to load calendars."
            )
            return PlatformWorkspaceActionListViewModel(
                title="Calendars",
                subtitle=message,
                empty_state=message,
            )
        calendars = result.data
        items = tuple(self._serialize_calendar(cal) for cal in calendars)
        return PlatformWorkspaceActionListViewModel(
            title="Calendars",
            subtitle="Operational working calendars for this organization.",
            empty_state="No calendars configured. A Global calendar is created automatically at startup.",
            items=items,
        )

    def _serialize_calendar(self, cal) -> PlatformWorkspaceActionItemViewModel:
        type_label = _CALENDAR_TYPE_LABELS.get(cal.calendar_type, cal.calendar_type.title())
        week_label = self._working_week_label(cal.id)
        usage_count = self._usage_count(cal.id)
        usage_label = f"{usage_count} assignment{'s' if usage_count != 1 else ''}" if usage_count else "No assignments"
        return PlatformWorkspaceActionItemViewModel(
            id=cal.id,
            title=cal.name,
            status_label=_calendar_status_label(cal.is_active),
            subtitle=week_label,
            supporting_text=f"{type_label} | {cal.timezone}",
            meta_text=usage_label,
            can_primary_action=True,
            can_secondary_action=False,
            state={
                "calendarId": cal.id,
                "organizationId": cal.organization_id,
                "code": cal.code,
                "name": cal.name,
                "description": cal.description,
                "calendarType": cal.calendar_type,
                "typeLabel": type_label,
                "timeZone": cal.timezone,
                "workingWeekLabel": week_label,
                "isDefault": cal.is_default,
                "isActive": cal.is_active,
                "effectiveFrom": cal.effective_from,
                "effectiveTo": cal.effective_to,
                "usageCount": usage_count,
                "usageLabel": usage_label,
                "updatedAt": cal.updated_at,
            },
        )

    def _working_week_label(self, calendar_id: str) -> str:
        result = self._platform_calendar_api.list_working_rules(calendar_id)
        if not result.ok or result.data is None:
            return "No working days configured"
        weekdays = tuple(
            sorted({rule.weekday for rule in result.data if rule.is_working_day})
        )
        return working_week_label(weekdays)

    def _usage_count(self, calendar_id: str) -> int:
        result = self._platform_calendar_api.list_calendar_assignments(calendar_id)
        if not result.ok or result.data is None:
            return 0
        groups = result.data
        return sum(len(groups.get(key, ())) for key in ("sites", "departments", "employees", "projects", "resources"))

    def calculate_working_day(
        self,
        payload: dict[str, Any],
    ) -> DesktopApiResult[WorkingDayCalculationDto]:
        """Working-day calculator — uses the calendar resolver via the API."""
        if self._platform_calendar_api is None:
            return preview_error_result("Calendar API is not connected.")
        start_date_str = string_value(payload, "startDate")
        if not start_date_str:
            from src.core.platform.api.desktop.models.common import DesktopApiError
            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(code="validation", message="Start date is required.", category="validation"),
            )
        working_days = int_value(payload, "workingDays")
        if working_days is None or working_days < 0:
            from src.core.platform.api.desktop.models.common import DesktopApiError
            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(code="validation", message="Working days must be >= 0.", category="validation"),
            )
        from src.core.platform.api.desktop.time_management.calendar.models.platform_calendar import (
            WorkingDaysCommand,
        )
        return self._platform_calendar_api.calculate_working_days(
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
