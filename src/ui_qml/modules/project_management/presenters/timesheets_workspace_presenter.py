from __future__ import annotations

from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementTimesheetsDesktopApi,
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
    build_project_management_timesheets_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetCollectionViewModel,
    TimesheetDetailFieldViewModel,
    TimesheetDetailViewModel,
    TimesheetMetricViewModel,
    TimesheetOverviewViewModel,
    TimesheetRecordViewModel,
    TimesheetSelectorOptionViewModel,
    TimesheetsWorkspaceViewModel,
)


class ProjectTimesheetsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementTimesheetsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_timesheets_desktop_api()

    def build_workspace_state(
        self,
        *,
        project_id: str = "all",
        assignment_id: str | None = None,
        period_start: str = "",
        queue_status: str = "SUBMITTED",
        selected_entry_id: str | None = None,
        selected_queue_period_id: str | None = None,
    ) -> TimesheetsWorkspaceViewModel:
        project_options = (
            TimesheetSelectorOptionViewModel(value="all", label="All projects"),
            *(
                TimesheetSelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_projects()
            ),
        )
        normalized_project_id = self._normalize_filter(
            project_id,
            project_options,
            default_value="all",
        )
        assignment_options = tuple(
            TimesheetSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_assignments(
                project_id=None if normalized_project_id == "all" else normalized_project_id
            )
        )
        resolved_assignment_id = self._resolve_selected_id(
            assignment_id,
            assignment_options,
        )
        queue_status_options = tuple(
            TimesheetSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_queue_statuses()
        )
        normalized_queue_status = self._normalize_filter(
            queue_status,
            queue_status_options,
            default_value="SUBMITTED",
        )
        snapshot = None
        if resolved_assignment_id:
            snapshot = self._desktop_api.build_assignment_snapshot(
                resolved_assignment_id,
                period_start=self._optional_date(period_start),
            )
        period_options = tuple(
            TimesheetSelectorOptionViewModel(value=option.value, label=option.label)
            for option in (snapshot.period_options if snapshot is not None else ())
        )
        resolved_period_start = snapshot.selected_period_start if snapshot is not None else ""
        resolved_selected_entry_id = self._resolve_selected_id(
            selected_entry_id,
            tuple(
                TimesheetSelectorOptionViewModel(value=entry.entry_id, label=entry.entry_date_label)
                for entry in (snapshot.entries if snapshot is not None else ())
            ),
        )
        selected_entry = next(
            (
                entry
                for entry in (snapshot.entries if snapshot is not None else ())
                if entry.entry_id == resolved_selected_entry_id
            ),
            None,
        )
        review_queue_rows = self._desktop_api.list_review_queue(status=normalized_queue_status)
        review_queue = TimesheetCollectionViewModel(
            title="Review Queue",
            subtitle="Submitted or locked periods waiting for review or follow-up.",
            empty_state=(
                "No periods match the current queue filter."
                if normalized_queue_status != "SUBMITTED"
                else "No submitted timesheet periods are waiting for review."
            ),
            items=tuple(self._to_review_queue_record(row) for row in review_queue_rows),
        )
        resolved_queue_period_id = self._resolve_selected_id(
            selected_queue_period_id,
            tuple(
                TimesheetSelectorOptionViewModel(value=row.period_id, label=row.resource_name)
                for row in review_queue_rows
            ),
        )
        review_detail = self._build_review_detail(resolved_queue_period_id)
        assignment_summary = self._build_assignment_summary(snapshot)
        entries_collection = TimesheetCollectionViewModel(
            title="Time Entries",
            subtitle="Period entries for the selected task assignment.",
            empty_state=(
                "Select a task assignment to review or capture labor entries."
                if snapshot is None
                else "No time entries are available yet for the selected period."
            ),
            items=tuple(
                self._to_entry_record(entry)
                for entry in (snapshot.entries if snapshot is not None else ())
            ),
        )
        overview = TimesheetOverviewViewModel(
            title="Timesheets",
            subtitle="Labor capture, month-end period status, and approver review from one PM workspace.",
            metrics=(
                TimesheetMetricViewModel(
                    label="Assignments",
                    value=str(len(assignment_options)),
                    supporting_text="Assignments available inside the current project scope.",
                ),
                TimesheetMetricViewModel(
                    label="Period entries",
                    value=str(len(snapshot.entries) if snapshot is not None else 0),
                    supporting_text=(
                        snapshot.scope_summary
                        if snapshot is not None
                        else "Select an assignment to inspect period hours."
                    ),
                ),
                TimesheetMetricViewModel(
                    label="Review queue",
                    value=str(len(review_queue_rows)),
                    supporting_text="Periods currently visible in the review lane.",
                ),
                TimesheetMetricViewModel(
                    label="Selected period",
                    value=(
                        snapshot.period_summary.status_label
                        if snapshot is not None
                        else "Not selected"
                    ),
                    supporting_text=(
                        snapshot.period_summary.period_start_label
                        if snapshot is not None
                        else "Choose an assignment first."
                    ),
                ),
            ),
        )
        empty_state = (
            ""
            if snapshot is not None or review_queue_rows
            else "No timesheet assignments or review periods are available in the current scope."
        )
        return TimesheetsWorkspaceViewModel(
            overview=overview,
            project_options=project_options,
            assignment_options=assignment_options,
            period_options=period_options,
            queue_status_options=queue_status_options,
            selected_project_id=normalized_project_id,
            selected_assignment_id=resolved_assignment_id,
            selected_period_start=resolved_period_start,
            selected_queue_status=normalized_queue_status,
            selected_entry_id=resolved_selected_entry_id,
            selected_queue_period_id=resolved_queue_period_id,
            assignment_summary=assignment_summary,
            entries=entries_collection,
            selected_entry_detail=self._build_selected_entry_detail(selected_entry),
            review_queue=review_queue,
            review_detail=review_detail,
            empty_state=empty_state,
        )

    def add_time_entry(self, payload: dict[str, Any]) -> None:
        command = TimesheetEntryCreateCommand(
            assignment_id=self._require_text(payload, "assignmentId", "Choose an assignment first."),
            entry_date=self._require_date(payload, "entryDate", "Entry date is required."),
            hours=self._require_float(payload, "hours", "Hours are required."),
            note=self._optional_text(payload, "note") or "",
        )
        self._desktop_api.add_time_entry(command)

    def update_time_entry(self, payload: dict[str, Any]) -> None:
        command = TimesheetEntryUpdateCommand(
            entry_id=self._require_text(payload, "entryId", "Choose an entry to update."),
            entry_date=self._require_date(payload, "entryDate", "Entry date is required."),
            hours=self._require_float(payload, "hours", "Hours are required."),
            note=self._optional_text(payload, "note") or "",
        )
        self._desktop_api.update_time_entry(command)

    def delete_time_entry(self, entry_id: str) -> None:
        normalized_entry_id = (entry_id or "").strip()
        if not normalized_entry_id:
            raise ValueError("Choose an entry to delete.")
        self._desktop_api.delete_time_entry(normalized_entry_id)

    def submit_period(self, payload: dict[str, Any]) -> None:
        self._desktop_api.submit_period(
            resource_id=self._require_text(payload, "resourceId", "Choose a resource period to submit."),
            period_start=self._require_date(payload, "periodStart", "Period start is required."),
            note=self._optional_text(payload, "note") or "",
        )

    def approve_period(self, payload: dict[str, Any]) -> None:
        self._desktop_api.approve_period(
            self._require_text(payload, "periodId", "Choose a period to approve."),
            note=self._optional_text(payload, "note") or "",
        )

    def reject_period(self, payload: dict[str, Any]) -> None:
        self._desktop_api.reject_period(
            self._require_text(payload, "periodId", "Choose a period to reject."),
            note=self._optional_text(payload, "note") or "",
        )

    def lock_period(self, payload: dict[str, Any]) -> None:
        self._desktop_api.lock_period(
            resource_id=self._require_text(payload, "resourceId", "Choose a resource period to lock."),
            period_start=self._require_date(payload, "periodStart", "Period start is required."),
            note=self._optional_text(payload, "note") or "",
        )

    def unlock_period(self, payload: dict[str, Any]) -> None:
        self._desktop_api.unlock_period(
            self._require_text(payload, "periodId", "Choose a period to unlock."),
            note=self._optional_text(payload, "note") or "",
        )

    @staticmethod
    def _build_assignment_summary(snapshot) -> TimesheetDetailViewModel:
        if snapshot is None:
            return TimesheetDetailViewModel(
                title="No assignment selected",
                empty_state="Select a task assignment to review entries, period status, and labor totals.",
            )
        summary = snapshot.period_summary
        return TimesheetDetailViewModel(
            id=snapshot.assignment.value,
            title=snapshot.assignment.label,
            status_label=summary.status_label,
            subtitle=f"{summary.period_start_label} -> {summary.period_end_label}",
            description=snapshot.scope_summary,
            fields=(
                TimesheetDetailFieldViewModel(
                    label="Resource",
                    value=summary.resource_name,
                ),
                TimesheetDetailFieldViewModel(
                    label="Hours",
                    value=summary.total_hours_label,
                    supporting_text=f"{summary.entry_count} entry or entries in the selected resource month.",
                ),
                TimesheetDetailFieldViewModel(
                    label="Submitted by",
                    value=summary.submitted_by_username,
                    supporting_text=summary.submitted_at_label,
                ),
                TimesheetDetailFieldViewModel(
                    label="Decision",
                    value=summary.decided_by_username,
                    supporting_text=summary.decided_at_label,
                ),
                TimesheetDetailFieldViewModel(
                    label="Decision note",
                    value=summary.decision_note or "No review note recorded.",
                ),
            ),
            state={
                "assignmentId": snapshot.assignment.value,
                "resourceId": summary.resource_id,
                "periodStart": snapshot.selected_period_start,
                "periodId": summary.period_id,
                "projectId": snapshot.assignment.project_id,
            },
        )

    @staticmethod
    def _build_selected_entry_detail(selected_entry) -> TimesheetDetailViewModel:
        if selected_entry is None:
            return TimesheetDetailViewModel(
                title="No entry selected",
                empty_state="Select an entry from the period list to review or edit its captured labor note.",
            )
        return TimesheetDetailViewModel(
            id=selected_entry.entry_id,
            title=selected_entry.entry_date_label,
            status_label=selected_entry.hours_label,
            subtitle=selected_entry.author_username,
            description=selected_entry.note or "No labor note recorded.",
            fields=(
                TimesheetDetailFieldViewModel(label="Date", value=selected_entry.entry_date_label),
                TimesheetDetailFieldViewModel(label="Hours", value=selected_entry.hours_label),
                TimesheetDetailFieldViewModel(label="Author", value=selected_entry.author_username),
            ),
            state={
                "entryId": selected_entry.entry_id,
                "entryDate": selected_entry.entry_date_label,
                "hours": str(selected_entry.hours),
                "note": selected_entry.note,
            },
        )

    def _build_review_detail(self, period_id: str) -> TimesheetDetailViewModel:
        if not period_id:
            return TimesheetDetailViewModel(
                title="No review period selected",
                empty_state="Select a review-queue period to inspect its entries and decide approval or rejection.",
            )
        detail = self._desktop_api.get_review_detail(period_id)
        summary = detail.summary
        entry_titles = ", ".join(entry.task_name for entry in detail.entries[:3])
        if len(detail.entries) > 3:
            entry_titles += ", ..."
        if not entry_titles:
            entry_titles = "No review entries recorded."
        return TimesheetDetailViewModel(
            id=summary.period_id,
            title=f"{summary.resource_name} | {summary.period_start_label}",
            status_label=summary.status_label,
            subtitle=" | ".join(summary.project_names) if summary.project_names else "Shared / cross-project scope",
            description=entry_titles,
            fields=(
                TimesheetDetailFieldViewModel(
                    label="Hours",
                    value=summary.total_hours_label,
                    supporting_text=f"{summary.entry_count} entry or entries.",
                ),
                TimesheetDetailFieldViewModel(
                    label="Submitted by",
                    value=summary.submitted_by_username,
                    supporting_text=summary.submitted_at_label,
                ),
                TimesheetDetailFieldViewModel(
                    label="Decided by",
                    value=summary.decided_by_username,
                    supporting_text=summary.decided_at_label,
                ),
                TimesheetDetailFieldViewModel(
                    label="Decision note",
                    value=summary.decision_note or "No decision note recorded.",
                ),
            ),
            state={
                "periodId": summary.period_id,
                "resourceId": summary.resource_id,
                "periodStart": summary.period_start.isoformat(),
                "status": summary.status,
            },
        )

    @staticmethod
    def _to_entry_record(entry) -> TimesheetRecordViewModel:
        return TimesheetRecordViewModel(
            id=entry.entry_id,
            title=entry.entry_date_label,
            status_label=entry.hours_label,
            subtitle=entry.author_username,
            supporting_text=entry.note or "No labor note recorded.",
            meta_text=f"Assignment entry {entry.entry_id}",
            state={
                "entryId": entry.entry_id,
                "entryDate": entry.entry_date_label,
                "hours": entry.hours,
                "note": entry.note,
            },
        )

    @staticmethod
    def _to_review_queue_record(row) -> TimesheetRecordViewModel:
        return TimesheetRecordViewModel(
            id=row.period_id,
            title=f"{row.resource_name} | {row.period_start_label}",
            status_label=row.status_label,
            subtitle=", ".join(row.project_names) if row.project_names else "Shared / cross-project scope",
            supporting_text=f"{row.total_hours_label} across {row.entry_count} entry or entries.",
            meta_text=f"Submitted by {row.submitted_by_username} at {row.submitted_at_label}",
            can_primary_action=False,
            can_secondary_action=False,
            state={
                "periodId": row.period_id,
                "resourceId": row.resource_id,
                "periodStart": row.period_start.isoformat(),
                "status": row.status,
            },
        )

    @staticmethod
    def _normalize_filter(value: str, options, *, default_value: str) -> str:
        normalized_value = (value or default_value).strip().lower()
        available_values = {
            str(option.value or "").strip().lower(): option.value
            for option in options
        }
        return available_values.get(normalized_value, default_value)

    @staticmethod
    def _resolve_selected_id(selected_id: str | None, options) -> str:
        normalized_id = (selected_id or "").strip()
        available_values = [str(option.value or "") for option in options]
        if normalized_id and normalized_id in available_values:
            return normalized_id
        return available_values[0] if available_values else ""

    @staticmethod
    def _require_text(payload: dict[str, Any], key: str, message: str) -> str:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str) -> str | None:
        value = str(payload.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _require_float(payload: dict[str, Any], key: str, message: str) -> float:
        value = payload.get(key)
        if value in (None, ""):
            raise ValueError(message)
        return float(value)

    @staticmethod
    def _require_date(payload: dict[str, Any], key: str, message: str) -> date:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Dates must use YYYY-MM-DD.") from exc

    @staticmethod
    def _optional_date(value: str) -> date | None:
        normalized_value = str(value or "").strip()
        if not normalized_value:
            return None
        try:
            return date.fromisoformat(normalized_value)
        except ValueError as exc:
            raise ValueError("Dates must use YYYY-MM-DD.") from exc


__all__ = ["ProjectTimesheetsWorkspacePresenter"]
