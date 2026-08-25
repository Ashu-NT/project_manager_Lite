from __future__ import annotations

import calendar
from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementTimesheetsDesktopApi,
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
    build_project_management_timesheets_desktop_api,
)
from src.core.platform.common.exceptions import NotFoundError


_WORKSPACE = {
    "routeId": "project_management.timesheets",
    "title": "Timesheets",
    "summary": "Review, correct, and submit your monthly time.",
}


def _owner_setup_state(
    *,
    period_start: date,
    page_size: int,
    sort_key: str,
    sort_direction: str,
    history_page_size: int,
) -> dict[str, object]:
    _, last_day = calendar.monthrange(period_start.year, period_start.month)
    period_end = period_start.replace(day=last_day)
    return {
        "workspace": dict(_WORKSPACE),
        "period": {
            "ownerAvailable": False,
            "periodStart": period_start.isoformat(),
            "periodEnd": period_end.isoformat(),
            "periodLabel": period_start.strftime("%B %Y"),
            "status": "UNAVAILABLE",
            "statusLabel": "Resource setup required",
            "setupMessage": (
                "Your user account is not linked to an active employee and project resource "
                "in this organization. Ask an administrator to complete that link before "
                "recording time."
            ),
            "totalHours": 0.0,
            "totalHoursLabel": "0.00 h",
            "entryCount": 0,
            "projectCount": 0,
            "taskCount": 0,
            "version": 0,
            "canAddEntry": False,
            "canEditEntry": False,
            "canDeleteEntry": False,
            "canSubmit": False,
            "canResubmit": False,
            "canViewReturnReason": False,
        },
        "entries": [],
        "entryTotal": 0,
        "entryPage": 1,
        "entryPageSize": page_size,
        "entrySortKey": sort_key,
        "entrySortDirection": sort_direction,
        "history": [],
        "historyTotal": 0,
        "historyPage": 1,
        "historyPageSize": history_page_size,
        "assignmentOptions": [],
        "projectOptions": [{"value": "all", "label": "All projects"}],
    }


def _period_map(period) -> dict[str, object]:
    return {
        "ownerAvailable": True,
        "periodId": period.period_id,
        "resourceId": period.resource_id,
        "resourceName": period.resource_name,
        "periodStart": period.period_start.isoformat(),
        "periodEnd": period.period_end.isoformat(),
        "periodLabel": period.period_label,
        "status": period.status,
        "statusLabel": period.status_label,
        "version": period.version,
        "totalHours": period.total_hours,
        "totalHoursLabel": period.total_hours_label,
        "entryCount": period.entry_count,
        "projectCount": period.project_count,
        "taskCount": period.task_count,
        "submittedAtLabel": period.submitted_at_label,
        "decidedAtLabel": period.decided_at_label,
        "returnReason": period.return_reason,
        "canAddEntry": period.can_add_entry,
        "canEditEntry": period.can_edit_entry,
        "canDeleteEntry": period.can_delete_entry,
        "canSubmit": period.can_submit,
        "canResubmit": period.can_resubmit,
        "canViewReturnReason": period.can_view_return_reason,
    }


def _entry_map(entry) -> dict[str, object]:
    return {
        "id": entry.entry_id,
        "entryId": entry.entry_id,
        "assignmentId": entry.assignment_id,
        "date": entry.work_date_label,
        "workDate": entry.work_date.isoformat(),
        "project": entry.project_name,
        "projectId": entry.project_id,
        "projectCode": entry.project_code,
        "task": entry.task_name,
        "taskId": entry.task_id,
        "taskCode": entry.task_code,
        "hours": entry.hours_label,
        "hoursValue": entry.hours,
        "description": entry.description,
        "activityType": entry.activity_type,
        "canEdit": entry.can_edit,
        "canDelete": entry.can_delete,
    }


class OwnerTimesheetsPresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementTimesheetsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_timesheets_desktop_api()

    def build_state(
        self,
        *,
        period_start: date,
        search_text: str,
        project_id: str,
        task_id: str,
        page: int,
        page_size: int,
        sort_key: str,
        sort_direction: str,
        history_page: int,
        history_page_size: int,
    ) -> dict[str, object]:
        try:
            period = self._desktop_api.get_owner_period(period_start=period_start)
        except NotFoundError as exc:
            if exc.code != "TIMESHEET_OWNER_RESOURCE_NOT_FOUND":
                raise
            return _owner_setup_state(
                period_start=period_start,
                page_size=page_size,
                sort_key=sort_key,
                sort_direction=sort_direction,
                history_page_size=history_page_size,
            )
        entries = self._desktop_api.list_owner_entries_page(
            period_start=period_start,
            search_text=search_text,
            project_id=None if project_id == "all" else project_id,
            task_id=None if task_id == "all" else task_id,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        history = self._desktop_api.list_owner_history_page(
            page=history_page,
            page_size=history_page_size,
        )
        owner_assignments = self._desktop_api.list_owner_assignments()
        project_options = {option.project_id: option.project_name for option in owner_assignments}
        return {
            "workspace": dict(_WORKSPACE),
            "period": _period_map(period),
            "entries": [_entry_map(item) for item in entries.items],
            "entryTotal": entries.total,
            "entryPage": entries.page,
            "entryPageSize": entries.page_size,
            "entrySortKey": entries.sort_key,
            "entrySortDirection": entries.sort_direction,
            "history": [_period_map(item) for item in history.items],
            "historyTotal": history.total,
            "historyPage": history.page,
            "historyPageSize": history.page_size,
            "assignmentOptions": [
                {
                    "value": option.value,
                    "label": f"{option.project_name} | {option.task_name}",
                    "projectId": option.project_id,
                    "projectName": option.project_name,
                    "taskId": option.task_id,
                    "taskName": option.task_name,
                }
                for option in owner_assignments
            ],
            "projectOptions": [
                {"value": "all", "label": "All projects"},
                *(
                    {"value": project_id, "label": name}
                    for project_id, name in sorted(
                        project_options.items(), key=lambda item: item[1].casefold()
                    )
                ),
            ],
        }

    def save_entry(self, payload: dict[str, Any]) -> None:
        entry_id = str(payload.get("entryId", "") or "").strip()
        entry_date = date.fromisoformat(str(payload.get("entryDate", "") or "").strip())
        period_start = date.fromisoformat(str(payload.get("periodStart", "") or "").strip())
        hours = float(payload.get("hours", 0) or 0)
        note = str(payload.get("note", "") or "").strip()
        if entry_id:
            self._desktop_api.update_owner_time_entry(
                TimesheetEntryUpdateCommand(
                    entry_id=entry_id,
                    entry_date=entry_date,
                    hours=hours,
                    note=note,
                ),
                period_start=period_start,
            )
            return
        assignment_id = str(payload.get("assignmentId", "") or "").strip()
        if not assignment_id:
            raise ValueError("Choose a task assignment before logging time.")
        self._desktop_api.add_owner_time_entry(
            TimesheetEntryCreateCommand(
                assignment_id=assignment_id,
                entry_date=entry_date,
                hours=hours,
                note=note,
            ),
            period_start=period_start,
        )

    def delete_entry(self, entry_id: str, *, period_start: date) -> None:
        normalized = str(entry_id or "").strip()
        if not normalized:
            raise ValueError("Choose a time entry to delete.")
        self._desktop_api.delete_owner_time_entry(
            normalized,
            period_start=period_start,
        )

    def submit_period(
        self,
        *,
        period_start: date,
        expected_version: int,
        note: str,
    ) -> None:
        self._desktop_api.submit_owner_period(
            period_start=period_start,
            expected_version=expected_version,
            note=note,
        )


__all__ = ["OwnerTimesheetsPresenter"]
