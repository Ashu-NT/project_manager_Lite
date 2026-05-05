from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_selector_options,
    serialize_timesheet_collection_view_model,
    serialize_timesheet_detail_view_model,
    serialize_timesheet_overview_view_model,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectTimesheetsWorkspacePresenter,
)


class ProjectManagementTimesheetsWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    assignmentOptionsChanged = Signal()
    periodOptionsChanged = Signal()
    queueStatusOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    selectedAssignmentIdChanged = Signal()
    selectedPeriodStartChanged = Signal()
    selectedQueueStatusChanged = Signal()
    selectedEntryIdChanged = Signal()
    selectedQueuePeriodIdChanged = Signal()
    assignmentSummaryChanged = Signal()
    entriesChanged = Signal()
    selectedEntryChanged = Signal()
    reviewQueueChanged = Signal()
    reviewDetailChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        timesheets_workspace_presenter: ProjectTimesheetsWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.timesheets"
        )
        self._timesheets_workspace_presenter = (
            timesheets_workspace_presenter or ProjectTimesheetsWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._project_options: list[dict[str, str]] = []
        self._assignment_options: list[dict[str, str]] = []
        self._period_options: list[dict[str, str]] = []
        self._queue_status_options: list[dict[str, str]] = []
        self._selected_project_id = "all"
        self._selected_assignment_id = ""
        self._selected_period_start = ""
        self._selected_queue_status = "SUBMITTED"
        self._selected_entry_id = ""
        self._selected_queue_period_id = ""
        self._assignment_summary: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "fields": [], "state": {}}
        self._entries: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._selected_entry: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "fields": [], "state": {}}
        self._review_queue: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._review_detail: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "fields": [], "state": {}}
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> list[dict[str, str]]:
        return self._project_options

    @Property("QVariantList", notify=assignmentOptionsChanged)
    def assignmentOptions(self) -> list[dict[str, str]]:
        return self._assignment_options

    @Property("QVariantList", notify=periodOptionsChanged)
    def periodOptions(self) -> list[dict[str, str]]:
        return self._period_options

    @Property("QVariantList", notify=queueStatusOptionsChanged)
    def queueStatusOptions(self) -> list[dict[str, str]]:
        return self._queue_status_options

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str:
        return self._selected_project_id

    @Property(str, notify=selectedAssignmentIdChanged)
    def selectedAssignmentId(self) -> str:
        return self._selected_assignment_id

    @Property(str, notify=selectedPeriodStartChanged)
    def selectedPeriodStart(self) -> str:
        return self._selected_period_start

    @Property(str, notify=selectedQueueStatusChanged)
    def selectedQueueStatus(self) -> str:
        return self._selected_queue_status

    @Property(str, notify=selectedEntryIdChanged)
    def selectedEntryId(self) -> str:
        return self._selected_entry_id

    @Property(str, notify=selectedQueuePeriodIdChanged)
    def selectedQueuePeriodId(self) -> str:
        return self._selected_queue_period_id

    @Property("QVariantMap", notify=assignmentSummaryChanged)
    def assignmentSummary(self) -> dict[str, object]:
        return self._assignment_summary

    @Property("QVariantMap", notify=entriesChanged)
    def entries(self) -> dict[str, object]:
        return self._entries

    @Property("QVariantMap", notify=selectedEntryChanged)
    def selectedEntry(self) -> dict[str, object]:
        return self._selected_entry

    @Property("QVariantMap", notify=reviewQueueChanged)
    def reviewQueue(self) -> dict[str, object]:
        return self._review_queue

    @Property("QVariantMap", notify=reviewDetailChanged)
    def reviewDetail(self) -> dict[str, object]:
        return self._review_detail

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(self._workspace_presenter.build_view_model())
            )
            workspace_state = self._timesheets_workspace_presenter.build_workspace_state(
                project_id=self._selected_project_id,
                assignment_id=self._selected_assignment_id or None,
                period_start=self._selected_period_start,
                queue_status=self._selected_queue_status,
                selected_entry_id=self._selected_entry_id or None,
                selected_queue_period_id=self._selected_queue_period_id or None,
            )
            self._set_overview(
                serialize_timesheet_overview_view_model(workspace_state.overview)
            )
            self._set_project_options(
                serialize_selector_options(workspace_state.project_options)
            )
            self._set_assignment_options(
                serialize_selector_options(workspace_state.assignment_options)
            )
            self._set_period_options(
                serialize_selector_options(workspace_state.period_options)
            )
            self._set_queue_status_options(
                serialize_selector_options(workspace_state.queue_status_options)
            )
            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_selected_assignment_id(workspace_state.selected_assignment_id)
            self._set_selected_period_start(workspace_state.selected_period_start)
            self._set_selected_queue_status(workspace_state.selected_queue_status)
            self._set_selected_entry_id(workspace_state.selected_entry_id)
            self._set_selected_queue_period_id(workspace_state.selected_queue_period_id)
            self._set_assignment_summary(
                serialize_timesheet_detail_view_model(workspace_state.assignment_summary)
            )
            self._set_entries(
                serialize_timesheet_collection_view_model(workspace_state.entries)
            )
            self._set_selected_entry(
                serialize_timesheet_detail_view_model(workspace_state.selected_entry_detail)
            )
            self._set_review_queue(
                serialize_timesheet_collection_view_model(workspace_state.review_queue)
            )
            self._set_review_detail(
                serialize_timesheet_detail_view_model(workspace_state.review_detail)
            )
            self._set_empty_state(workspace_state.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        normalized_value = (project_id or "").strip() or "all"
        if normalized_value == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_value)
        self._set_selected_assignment_id("")
        self._set_selected_period_start("")
        self._set_selected_entry_id("")
        self.refresh()

    @Slot(str)
    def selectAssignment(self, assignment_id: str) -> None:
        normalized_value = (assignment_id or "").strip()
        if normalized_value == self._selected_assignment_id:
            return
        self._set_selected_assignment_id(normalized_value)
        self._set_selected_period_start("")
        self._set_selected_entry_id("")
        self.refresh()

    @Slot(str)
    def selectPeriod(self, period_start: str) -> None:
        normalized_value = (period_start or "").strip()
        if normalized_value == self._selected_period_start:
            return
        self._set_selected_period_start(normalized_value)
        self._set_selected_entry_id("")
        self.refresh()

    @Slot(str)
    def setQueueStatus(self, queue_status: str) -> None:
        normalized_value = (queue_status or "").strip().upper() or "SUBMITTED"
        if normalized_value == self._selected_queue_status:
            return
        self._set_selected_queue_status(normalized_value)
        self._set_selected_queue_period_id("")
        self.refresh()

    @Slot(str)
    def selectEntry(self, entry_id: str) -> None:
        normalized_value = (entry_id or "").strip()
        if normalized_value == self._selected_entry_id:
            return
        self._set_selected_entry_id(normalized_value)
        self.refresh()

    @Slot(str)
    def selectQueuePeriod(self, period_id: str) -> None:
        normalized_value = (period_id or "").strip()
        if normalized_value == self._selected_queue_period_id:
            return
        self._set_selected_queue_period_id(normalized_value)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def addTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._timesheets_workspace_presenter.add_time_entry(dict(payload)),
            success_message="Time entry added.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._timesheets_workspace_presenter.update_time_entry(dict(payload)),
            success_message="Time entry updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteTimeEntry(self, entry_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._timesheets_workspace_presenter.delete_time_entry(entry_id),
            success_message="Time entry deleted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def submitPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._timesheets_workspace_presenter.submit_period(dict(payload)),
            success_message="Timesheet period submitted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def approvePeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._timesheets_workspace_presenter.approve_period(dict(payload)),
            success_message="Timesheet period approved.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def rejectPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._timesheets_workspace_presenter.reject_period(dict(payload)),
            success_message="Timesheet period rejected.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def lockPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._timesheets_workspace_presenter.lock_period(dict(payload)),
            success_message="Timesheet period locked.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def unlockPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._timesheets_workspace_presenter.unlock_period(dict(payload)),
            success_message="Timesheet period unlocked.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "timesheet_period",
            "project_tasks",
            "resource",
            scope_code="project_management",
        )

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_project_options(self, project_options: list[dict[str, str]]) -> None:
        if project_options == self._project_options:
            return
        self._project_options = project_options
        self.projectOptionsChanged.emit()

    def _set_assignment_options(self, assignment_options: list[dict[str, str]]) -> None:
        if assignment_options == self._assignment_options:
            return
        self._assignment_options = assignment_options
        self.assignmentOptionsChanged.emit()

    def _set_period_options(self, period_options: list[dict[str, str]]) -> None:
        if period_options == self._period_options:
            return
        self._period_options = period_options
        self.periodOptionsChanged.emit()

    def _set_queue_status_options(self, queue_status_options: list[dict[str, str]]) -> None:
        if queue_status_options == self._queue_status_options:
            return
        self._queue_status_options = queue_status_options
        self.queueStatusOptionsChanged.emit()

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()

    def _set_selected_assignment_id(self, selected_assignment_id: str) -> None:
        if selected_assignment_id == self._selected_assignment_id:
            return
        self._selected_assignment_id = selected_assignment_id
        self.selectedAssignmentIdChanged.emit()

    def _set_selected_period_start(self, selected_period_start: str) -> None:
        if selected_period_start == self._selected_period_start:
            return
        self._selected_period_start = selected_period_start
        self.selectedPeriodStartChanged.emit()

    def _set_selected_queue_status(self, selected_queue_status: str) -> None:
        if selected_queue_status == self._selected_queue_status:
            return
        self._selected_queue_status = selected_queue_status
        self.selectedQueueStatusChanged.emit()

    def _set_selected_entry_id(self, selected_entry_id: str) -> None:
        if selected_entry_id == self._selected_entry_id:
            return
        self._selected_entry_id = selected_entry_id
        self.selectedEntryIdChanged.emit()

    def _set_selected_queue_period_id(self, selected_queue_period_id: str) -> None:
        if selected_queue_period_id == self._selected_queue_period_id:
            return
        self._selected_queue_period_id = selected_queue_period_id
        self.selectedQueuePeriodIdChanged.emit()

    def _set_assignment_summary(self, assignment_summary: dict[str, object]) -> None:
        if assignment_summary == self._assignment_summary:
            return
        self._assignment_summary = assignment_summary
        self.assignmentSummaryChanged.emit()

    def _set_entries(self, entries: dict[str, object]) -> None:
        if entries == self._entries:
            return
        self._entries = entries
        self.entriesChanged.emit()

    def _set_selected_entry(self, selected_entry: dict[str, object]) -> None:
        if selected_entry == self._selected_entry:
            return
        self._selected_entry = selected_entry
        self.selectedEntryChanged.emit()

    def _set_review_queue(self, review_queue: dict[str, object]) -> None:
        if review_queue == self._review_queue:
            return
        self._review_queue = review_queue
        self.reviewQueueChanged.emit()

    def _set_review_detail(self, review_detail: dict[str, object]) -> None:
        if review_detail == self._review_detail:
            return
        self._review_detail = review_detail
        self.reviewDetailChanged.emit()


__all__ = ["ProjectManagementTimesheetsWorkspaceController"]
