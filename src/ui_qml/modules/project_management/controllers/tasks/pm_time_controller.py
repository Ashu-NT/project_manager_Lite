from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from src.ui_qml.modules.project_management.controllers.common import (
    run_mutation,
    serialize_selector_options,
    serialize_timesheet_collection_view_model,
    serialize_timesheet_detail_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectTasksWorkspacePresenter,
)


class PMTimeController(QObject):
    """Owns time-tracking domain data and time-entry mutations."""

    timeAssignmentOptionsChanged = Signal()
    timePeriodOptionsChanged = Signal()
    timeAssignmentSummaryChanged = Signal()
    timeEntriesChanged = Signal()
    selectedTimeEntryChanged = Signal()

    def __init__(
        self,
        *,
        presenter: ProjectTasksWorkspacePresenter,
        facade_refresh: Callable[[], None],
        refresh_time_entries: Callable[[], None] | None = None,
        set_is_busy: Callable[[bool], None],
        set_error_message: Callable[[str], None],
        set_feedback_message: Callable[[str], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._facade_refresh = facade_refresh
        # Scoped refresh for entry-level mutations — avoids full workspace reload
        self._refresh_entry_cb = refresh_time_entries if refresh_time_entries is not None else facade_refresh
        self._set_is_busy = set_is_busy
        self._set_error_message = set_error_message
        self._set_feedback_message = set_feedback_message
        self._time_assignment_options: list[dict[str, str]] = []
        self._time_period_options: list[dict[str, str]] = []
        self._time_assignment_summary: dict[str, object] = {
            "id": "", "title": "", "statusLabel": "", "subtitle": "",
            "description": "", "emptyState": "", "fields": [], "state": {},
        }
        self._time_entries_table_model = DynamicTableModel(self)
        self._time_entries: dict[str, object] = {
            "title": "", "subtitle": "", "emptyState": "", "items": []
        }
        self._selected_time_entry: dict[str, object] = {
            "id": "", "title": "", "statusLabel": "", "subtitle": "",
            "description": "", "emptyState": "", "fields": [], "state": {},
        }

    # ── Populate from workspace state ────────────────────────────────

    def _update(self, workspace_state: object) -> None:
        self._set_time_assignment_options(
            serialize_selector_options(workspace_state.assignment_options)
        )
        self._set_time_period_options(
            serialize_selector_options(workspace_state.time_period_options)
        )
        self._set_time_assignment_summary(
            serialize_timesheet_detail_view_model(workspace_state.time_assignment_summary)
        )
        self._set_time_entries(
            serialize_timesheet_collection_view_model(workspace_state.time_entries)
        )
        self._set_selected_time_entry(
            serialize_timesheet_detail_view_model(
                workspace_state.selected_time_entry_detail
            )
        )

    # ── Properties ───────────────────────────────────────────────────

    @Property("QVariantList", notify=timeAssignmentOptionsChanged)
    def timeAssignmentOptions(self) -> list[dict[str, str]]:
        return self._time_assignment_options

    @Property("QVariantList", notify=timePeriodOptionsChanged)
    def timePeriodOptions(self) -> list[dict[str, str]]:
        return self._time_period_options

    @Property("QVariantMap", notify=timeAssignmentSummaryChanged)
    def timeAssignmentSummary(self) -> dict[str, object]:
        return self._time_assignment_summary

    @Property("QVariantMap", notify=timeEntriesChanged)
    def timeEntries(self) -> dict[str, object]:
        return self._time_entries

    @Property(QObject, constant=True)
    def timeEntriesTableModel(self) -> DynamicTableModel:
        return self._time_entries_table_model

    @Property("QVariantMap", notify=selectedTimeEntryChanged)
    def selectedTimeEntry(self) -> dict[str, object]:
        return self._selected_time_entry

    # ── Mutation slots ────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def addTaskTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.add_task_time_entry(dict(payload)),
            success_message="Task time entry added.",
            on_success=self._refresh_entry_cb,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateTaskTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.update_task_time_entry(dict(payload)),
            success_message="Task time entry updated.",
            on_success=self._refresh_entry_cb,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteTaskTimeEntry(self, entry_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.delete_task_time_entry(entry_id),
            success_message="Task time entry deleted.",
            on_success=self._refresh_entry_cb,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def submitTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.submit_task_period(dict(payload)),
            success_message="Task period submitted.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def lockTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.lock_task_period(dict(payload)),
            success_message="Task period locked.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def unlockTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._presenter.unlock_task_period(dict(payload)),
            success_message="Task period unlocked.",
            on_success=self._facade_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    # ── Private setters ───────────────────────────────────────────────

    def _set_time_assignment_options(self, v: list) -> None:
        if v == self._time_assignment_options:
            return
        self._time_assignment_options = v
        self.timeAssignmentOptionsChanged.emit()

    def _set_time_period_options(self, v: list) -> None:
        if v == self._time_period_options:
            return
        self._time_period_options = v
        self.timePeriodOptionsChanged.emit()

    def _set_time_assignment_summary(self, v: dict) -> None:
        if v == self._time_assignment_summary:
            return
        self._time_assignment_summary = v
        self.timeAssignmentSummaryChanged.emit()

    def _set_time_entries(self, v: dict) -> None:
        if v == self._time_entries:
            return
        self._time_entries = v
        self._time_entries_table_model.set_rows(v.get("items", []))
        self.timeEntriesChanged.emit()

    def _set_selected_time_entry(self, v: dict) -> None:
        if v == self._selected_time_entry:
            return
        self._selected_time_entry = v
        self.selectedTimeEntryChanged.emit()


__all__ = ["PMTimeController"]
