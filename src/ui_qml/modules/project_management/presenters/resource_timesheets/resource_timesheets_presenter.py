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
        "resourceSelected": True,
        "periodId": period.period_id,
        "resourceId": period.resource_id,
        "resourceName": period.resource_name,
        "resourceCode": period.resource_code,
        "resourceKind": period.resource_kind,
        "workerType": period.worker_type,
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
        "canViewHistory": period.can_view_history,
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
        "version": entry.version,
        "canEdit": entry.can_edit,
        "canDelete": entry.can_delete,
    }


class ResourceTimesheetsPresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementTimesheetsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_timesheets_desktop_api()

    def build_state(
        self,
        *,
        scope: str,
        resource_id: str,
        resource_search_text: str,
        resource_page: int,
        resource_page_size: int,
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
        access = self._desktop_api.get_timesheet_workspace_access()
        available = tuple(access.available_scopes)
        resolved_scope = scope if scope in available else access.default_scope
        target_resource_id = access.mine_resource_id if resolved_scope == "mine" else resource_id
        resource_page_result = None
        if resolved_scope in {"team", "all"}:
            resource_page_result = self._desktop_api.list_timesheet_resources_page(
                scope=resolved_scope,
                search_text=resource_search_text,
                page=resource_page,
                page_size=resource_page_size,
            )
        scope_options = [
            {"value": value, "label": {"mine": "Mine", "team": "My Team", "all": "All Resources"}[value]}
            for value in available
        ]
        resources = [
            {
                "value": item.resource_id,
                "label": item.resource_name,
                "code": item.resource_code,
                "kind": item.kind,
                "workerType": item.worker_type,
            }
            for item in (resource_page_result.items if resource_page_result else ())
        ]
        common = {
            "selectedScope": resolved_scope,
            "availableScopes": list(available),
            "scopeOptions": scope_options,
            "canSelectScope": len(available) > 1,
            "canSelectResource": resolved_scope in {"team", "all"},
            "selectedResourceId": target_resource_id,
            "resourceOptions": resources,
            "resourceTotal": resource_page_result.total if resource_page_result else 0,
            "resourcePage": resource_page_result.page if resource_page_result else 1,
            "resourcePageSize": resource_page_result.page_size if resource_page_result else resource_page_size,
        }
        if not target_resource_id:
            state = _owner_setup_state(
                period_start=period_start,
                page_size=page_size,
                sort_key=sort_key,
                sort_direction=sort_direction,
                history_page_size=history_page_size,
            )
            state["period"].update(
                {
                    "ownerAvailable": resolved_scope != "mine",
                    "resourceSelected": False,
                    "statusLabel": (
                        "Resource setup required" if resolved_scope == "mine" else "Select a Resource"
                    ),
                    "setupMessage": (
                        state["period"]["setupMessage"]
                        if resolved_scope == "mine"
                        else "Search for and select an eligible Resource to view its Timesheet."
                    ),
                }
            )
            state.update(common)
            return state
        period = self._desktop_api.get_resource_timesheet_period(
            scope=resolved_scope,
            resource_id=target_resource_id,
            period_start=period_start,
        )
        entries = self._desktop_api.list_resource_timesheet_entries_page(
            scope=resolved_scope,
            resource_id=target_resource_id,
            period_start=period_start,
            search_text=search_text,
            project_id=None if project_id == "all" else project_id,
            task_id=None if task_id == "all" else task_id,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        history = self._desktop_api.list_resource_timesheet_history_page(
            scope=resolved_scope,
            resource_id=target_resource_id,
            page=history_page,
            page_size=history_page_size,
        )
        assignments = self._desktop_api.list_resource_assignments(resource_id=target_resource_id)
        project_options = {option.project_id: option.project_name for option in assignments}
        result = {
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
                for option in assignments
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
        result.update(common)
        return result

    def save_entry(self, payload: dict[str, Any]) -> None:
        scope = str(payload.get("scope", "mine") or "mine").strip()
        resource_id = str(payload.get("resourceId", "") or "").strip() or None
        entry_id = str(payload.get("entryId", "") or "").strip()
        entry_date = date.fromisoformat(str(payload.get("entryDate", "") or "").strip())
        period_start = date.fromisoformat(str(payload.get("periodStart", "") or "").strip())
        hours = float(payload.get("hours", 0) or 0)
        note = str(payload.get("note", "") or "").strip()
        if entry_id:
            expected_version = int(payload.get("expectedVersion", 0) or 0)
            if expected_version < 1:
                raise ValueError("Refresh the time entry before changing it.")
            self._desktop_api.update_resource_time_entry(
                TimesheetEntryUpdateCommand(
                    entry_id=entry_id,
                    expected_version=expected_version,
                    entry_date=entry_date,
                    hours=hours,
                    note=note,
                ),
                scope=scope,
                resource_id=resource_id,
                period_start=period_start,
            )
            return
        assignment_id = str(payload.get("assignmentId", "") or "").strip()
        if not assignment_id:
            raise ValueError("Choose a task assignment before logging time.")
        self._desktop_api.add_resource_time_entry(
            TimesheetEntryCreateCommand(
                assignment_id=assignment_id,
                entry_date=entry_date,
                hours=hours,
                note=note,
            ),
            scope=scope,
            resource_id=resource_id,
            period_start=period_start,
        )

    def delete_entry(
        self,
        entry_id: str,
        *,
        expected_version: int,
        scope: str,
        resource_id: str | None,
        period_start: date,
    ) -> None:
        normalized = str(entry_id or "").strip()
        if not normalized:
            raise ValueError("Choose a time entry to delete.")
        if expected_version < 1:
            raise ValueError("Refresh the time entry before deleting it.")
        self._desktop_api.delete_resource_time_entry(
            normalized,
            scope=scope,
            resource_id=resource_id,
            period_start=period_start,
            expected_version=expected_version,
        )

    def submit_period(
        self,
        *,
        scope: str,
        resource_id: str | None,
        period_start: date,
        expected_version: int,
        note: str,
    ) -> None:
        self._desktop_api.submit_resource_timesheet_period(
            scope=scope,
            resource_id=resource_id,
            period_start=period_start,
            expected_version=expected_version,
            note=note,
        )


__all__ = ["ResourceTimesheetsPresenter"]
