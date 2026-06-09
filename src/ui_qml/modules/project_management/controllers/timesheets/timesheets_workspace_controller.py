from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
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
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from .detail_builder import build_entry_detail
from .domain_event_binder import bind_timesheets_domain_events
from .mutation_handler import TimesheetsMutationHandler
from .review_queue_controller import (
    clear_queue_bulk_selection,
    load_queue_period_detail,
    select_visible_queue_periods,
    set_queue_bulk_selection,
    set_queue_page,
    set_queue_page_size,
)
from .selection_handler import (
    select_assignment,
    select_period,
    select_project,
    set_queue_status,
)
from .state import (
    default_assignment_summary,
    default_entries,
    default_overview,
    default_review_detail,
    default_review_queue,
    default_selected_entry,
)
from .table_models import create_timesheets_table_models

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
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
    queuePageChanged = Signal()
    queuePageSizeChanged = Signal()
    queueTotalCountChanged = Signal()
    selectedQueuePeriodIdsChanged = Signal()
    selectedQueuePeriodCountChanged = Signal()

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
        self._table_models = create_timesheets_table_models(self)
        self._mutations = TimesheetsMutationHandler(
            presenter=self._timesheets_workspace_presenter,
            request_domain_refresh=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )
        self._overview: dict[str, object] = default_overview()
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
        self._assignment_summary: dict[str, object] = default_assignment_summary()
        self._entries: dict[str, object] = default_entries()
        self._selected_entry: dict[str, object] = default_selected_entry()
        self._review_queue: dict[str, object] = default_review_queue()
        self._review_detail: dict[str, object] = default_review_detail()
        self._queue_page = 1
        self._queue_page_size = 25
        self._queue_total_count = 0
        self._selected_queue_period_ids: list[str] = []
        bind_timesheets_domain_events(self)
        self.refresh()

    # ── Properties ────────────────────────────────────────────────────

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

    @Property(QObject, constant=True)
    def entriesTableModel(self) -> DynamicTableModel:
        return self._table_models.entries

    @Property(QObject, constant=True)
    def reviewQueueTableModel(self) -> DynamicTableModel:
        return self._table_models.review_queue

    @Property("QVariantMap", notify=reviewDetailChanged)
    def reviewDetail(self) -> dict[str, object]:
        return self._review_detail

    @Property(int, notify=queuePageChanged)
    def queuePage(self) -> int:
        return self._queue_page

    @Property(int, notify=queuePageSizeChanged)
    def queuePageSize(self) -> int:
        return self._queue_page_size

    @Property(int, notify=queueTotalCountChanged)
    def queueTotalCount(self) -> int:
        return self._queue_total_count

    @Property("QVariantList", notify=selectedQueuePeriodIdsChanged)
    def selectedQueuePeriodIds(self) -> list[str]:
        return self._selected_queue_period_ids

    @Property(int, notify=selectedQueuePeriodCountChanged)
    def selectedQueuePeriodCount(self) -> int:
        return len(self._selected_queue_period_ids)

    # ── Refresh ───────────────────────────────────────────────────────

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
            self._set_queue_total_count(len(self._review_queue.get("items") or []))
            self._set_review_detail(
                serialize_timesheet_detail_view_model(workspace_state.review_detail)
            )
            self._set_empty_state(workspace_state.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    # ── Selection slots ───────────────────────────────────────────────

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        select_project(self, project_id)

    @Slot(str)
    def selectAssignment(self, assignment_id: str) -> None:
        select_assignment(self, assignment_id)

    @Slot(str)
    def selectPeriod(self, period_start: str) -> None:
        select_period(self, period_start)

    @Slot(str)
    def setQueueStatus(self, queue_status: str) -> None:
        set_queue_status(self, queue_status)

    @Slot(str)
    def selectEntry(self, entry_id: str) -> None:
        normalized = (entry_id or "").strip()
        if normalized == self._selected_entry_id:
            return
        self._set_selected_entry_id(normalized)
        self._set_selected_entry(build_entry_detail(normalized, self._entries))

    @Slot(str)
    def selectQueuePeriod(self, period_id: str) -> None:
        normalized = (period_id or "").strip()
        if normalized == self._selected_queue_period_id:
            return
        self._set_selected_queue_period_id(normalized)
        load_queue_period_detail(self, normalized)

    # ── Queue management slots ────────────────────────────────────────

    @Slot(int)
    def setQueuePage(self, page: int) -> None:
        set_queue_page(self, page)

    @Slot(int)
    def setQueuePageSize(self, page_size: int) -> None:
        set_queue_page_size(self, page_size)

    @Slot(str, bool)
    def setQueueBulkSelection(self, period_id: str, selected: bool) -> None:
        set_queue_bulk_selection(self, period_id, selected)

    @Slot()
    def selectVisibleQueuePeriods(self) -> None:
        select_visible_queue_periods(self)

    @Slot()
    def clearQueueBulkSelection(self) -> None:
        clear_queue_bulk_selection(self)

    @Slot()
    def exportTimesheets(self) -> None:
        self._set_error_message("")
        self._set_feedback_message(
            "Export is not available here. Open the Reports section to generate timesheet summaries and period exports."
        )

    # ── Mutation slots ────────────────────────────────────────────────

    @Slot("QVariantList", result="QVariantMap")
    def bulkApprovePeriods(self, period_ids: list) -> dict[str, object]:
        return self._mutations.bulk_approve_periods(period_ids)

    @Slot("QVariantList", result="QVariantMap")
    def bulkRejectPeriods(self, period_ids: list) -> dict[str, object]:
        return self._mutations.bulk_reject_periods(period_ids)

    @Slot("QVariantMap", result="QVariantMap")
    def addTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.add_time_entry(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.update_time_entry(payload)

    @Slot(str, result="QVariantMap")
    def deleteTimeEntry(self, entry_id: str) -> dict[str, object]:
        return self._mutations.delete_time_entry(entry_id)

    @Slot("QVariantMap", result="QVariantMap")
    def submitPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.submit_period(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def approvePeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.approve_period(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def rejectPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.reject_period(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def lockPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.lock_period(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def unlockPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.unlock_period(payload)

    # ── State setters ─────────────────────────────────────────────────

    def _set_overview(self, v: dict[str, object]) -> None:
        if v == self._overview:
            return
        self._overview = v
        self.overviewChanged.emit()

    def _set_project_options(self, v: list[dict[str, str]]) -> None:
        if v == self._project_options:
            return
        self._project_options = v
        self.projectOptionsChanged.emit()

    def _set_assignment_options(self, v: list[dict[str, str]]) -> None:
        if v == self._assignment_options:
            return
        self._assignment_options = v
        self.assignmentOptionsChanged.emit()

    def _set_period_options(self, v: list[dict[str, str]]) -> None:
        if v == self._period_options:
            return
        self._period_options = v
        self.periodOptionsChanged.emit()

    def _set_queue_status_options(self, v: list[dict[str, str]]) -> None:
        if v == self._queue_status_options:
            return
        self._queue_status_options = v
        self.queueStatusOptionsChanged.emit()

    def _set_selected_project_id(self, v: str) -> None:
        if v == self._selected_project_id:
            return
        self._selected_project_id = v
        self.selectedProjectIdChanged.emit()

    def _set_selected_assignment_id(self, v: str) -> None:
        if v == self._selected_assignment_id:
            return
        self._selected_assignment_id = v
        self.selectedAssignmentIdChanged.emit()

    def _set_selected_period_start(self, v: str) -> None:
        if v == self._selected_period_start:
            return
        self._selected_period_start = v
        self.selectedPeriodStartChanged.emit()

    def _set_selected_queue_status(self, v: str) -> None:
        if v == self._selected_queue_status:
            return
        self._selected_queue_status = v
        self.selectedQueueStatusChanged.emit()

    def _set_selected_entry_id(self, v: str) -> None:
        if v == self._selected_entry_id:
            return
        self._selected_entry_id = v
        self.selectedEntryIdChanged.emit()

    def _set_selected_queue_period_id(self, v: str) -> None:
        if v == self._selected_queue_period_id:
            return
        self._selected_queue_period_id = v
        self.selectedQueuePeriodIdChanged.emit()

    def _set_assignment_summary(self, v: dict[str, object]) -> None:
        if v == self._assignment_summary:
            return
        self._assignment_summary = v
        self.assignmentSummaryChanged.emit()

    def _set_entries(self, v: dict[str, object]) -> None:
        if v == self._entries:
            return
        self._entries = v
        self._table_models.entries.set_rows(v.get("items", []))
        self.entriesChanged.emit()

    def _set_selected_entry(self, v: dict[str, object]) -> None:
        if v == self._selected_entry:
            return
        self._selected_entry = v
        self.selectedEntryChanged.emit()

    def _set_review_queue(self, v: dict[str, object]) -> None:
        if v == self._review_queue:
            return
        self._review_queue = v
        self._table_models.review_queue.set_rows(v.get("items", []))
        self.reviewQueueChanged.emit()

    def _set_review_detail(self, v: dict[str, object]) -> None:
        if v == self._review_detail:
            return
        self._review_detail = v
        self.reviewDetailChanged.emit()

    def _set_queue_page(self, v: int) -> None:
        if v == self._queue_page:
            return
        self._queue_page = v
        self.queuePageChanged.emit()

    def _set_queue_total_count(self, v: int) -> None:
        if v == self._queue_total_count:
            return
        self._queue_total_count = v
        self.queueTotalCountChanged.emit()

    def _set_selected_queue_period_ids(self, ids: list[str]) -> None:
        if ids == self._selected_queue_period_ids:
            return
        self._selected_queue_period_ids = ids
        self.selectedQueuePeriodIdsChanged.emit()
        self.selectedQueuePeriodCountChanged.emit()


__all__ = ["ProjectManagementTimesheetsWorkspaceController"]
