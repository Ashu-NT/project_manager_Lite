from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import ProjectManagementWorkspaceControllerBase
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectTimesheetsWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from . import state_setters as _setters
from .domain_event_binder import bind_timesheets_domain_events
from .mutation_handler import TimesheetsMutationHandler
from .refresh_service import refresh_timesheets_workspace
from .review_queue_controller import (
    load_queue_period_detail,
    set_queue_page,
    set_queue_page_size,
    set_queue_period_range,
    set_queue_project,
    set_queue_resource,
    set_queue_search_text,
    set_queue_sort,
)
from .selection_handler import set_queue_status
from .state import default_overview, default_review_detail, default_review_queue

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementTimesheetsWorkspaceController(ProjectManagementWorkspaceControllerBase):
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    queueStatusOptionsChanged = Signal()
    queueResourceOptionsChanged = Signal()
    selectedQueueStatusChanged = Signal()
    selectedQueuePeriodIdChanged = Signal()
    reviewQueueChanged = Signal()
    reviewDetailChanged = Signal()
    queuePageChanged = Signal()
    queuePageSizeChanged = Signal()
    queueTotalCountChanged = Signal()
    queueSearchTextChanged = Signal()
    selectedQueueProjectIdChanged = Signal()
    selectedQueueResourceIdChanged = Signal()
    queuePeriodStartFromChanged = Signal()
    queuePeriodStartToChanged = Signal()
    queueSortKeyChanged = Signal()
    queueSortDirectionChanged = Signal()

    def __init__(self, *, workspace_presenter=None, timesheets_workspace_presenter=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter("project_management.timesheets")
        self._timesheets_workspace_presenter = timesheets_workspace_presenter or ProjectTimesheetsWorkspacePresenter()
        self._review_queue_table_model = DynamicTableModel(self)
        self._mutations = TimesheetsMutationHandler(
            presenter=self._timesheets_workspace_presenter,
            request_domain_refresh=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )
        self._overview = default_overview()
        self._project_options = []
        self._queue_status_options = []
        self._queue_resource_options = []
        self._selected_queue_status = "SUBMITTED"
        self._selected_queue_period_id = ""
        self._review_queue = default_review_queue()
        self._review_detail = default_review_detail()
        self._queue_page = 1
        self._queue_page_size = 25
        self._queue_total_count = 0
        self._queue_search_text = ""
        self._selected_queue_project_id = "all"
        self._selected_queue_resource_id = "all"
        self._queue_period_start_from = ""
        self._queue_period_start_to = ""
        self._queue_sort_key = "submittedAt"
        self._queue_sort_direction = 1
        bind_timesheets_domain_events(self)
        self.refresh()

    overview = Property("QVariantMap", lambda self: self._overview, notify=overviewChanged)
    projectOptions = Property("QVariantList", lambda self: self._project_options, notify=projectOptionsChanged)
    queueStatusOptions = Property("QVariantList", lambda self: self._queue_status_options, notify=queueStatusOptionsChanged)
    queueResourceOptions = Property("QVariantList", lambda self: self._queue_resource_options, notify=queueResourceOptionsChanged)
    selectedQueueStatus = Property(str, lambda self: self._selected_queue_status, notify=selectedQueueStatusChanged)
    selectedQueuePeriodId = Property(str, lambda self: self._selected_queue_period_id, notify=selectedQueuePeriodIdChanged)
    reviewQueue = Property("QVariantMap", lambda self: self._review_queue, notify=reviewQueueChanged)
    reviewDetail = Property("QVariantMap", lambda self: self._review_detail, notify=reviewDetailChanged)
    queuePage = Property(int, lambda self: self._queue_page, notify=queuePageChanged)
    queuePageSize = Property(int, lambda self: self._queue_page_size, notify=queuePageSizeChanged)
    queueTotalCount = Property(int, lambda self: self._queue_total_count, notify=queueTotalCountChanged)
    queueSearchText = Property(str, lambda self: self._queue_search_text, notify=queueSearchTextChanged)
    selectedQueueProjectId = Property(str, lambda self: self._selected_queue_project_id, notify=selectedQueueProjectIdChanged)
    selectedQueueResourceId = Property(str, lambda self: self._selected_queue_resource_id, notify=selectedQueueResourceIdChanged)
    queuePeriodStartFrom = Property(str, lambda self: self._queue_period_start_from, notify=queuePeriodStartFromChanged)
    queuePeriodStartTo = Property(str, lambda self: self._queue_period_start_to, notify=queuePeriodStartToChanged)
    queueSortKey = Property(str, lambda self: self._queue_sort_key, notify=queueSortKeyChanged)
    queueSortDirection = Property(int, lambda self: self._queue_sort_direction, notify=queueSortDirectionChanged)
    reviewQueueTableModel = Property(QObject, lambda self: self._review_queue_table_model, constant=True)

    @Slot()
    def refresh(self) -> None: refresh_timesheets_workspace(self)

    @Slot(str)
    def setQueueStatus(self, value: str) -> None: set_queue_status(self, value)

    @Slot(str)
    def selectQueuePeriod(self, period_id: str) -> None:
        normalized = str(period_id or "").strip()
        if normalized != self._selected_queue_period_id:
            self._set_selected_queue_period_id(normalized)
            load_queue_period_detail(self, normalized)

    @Slot(int)
    def setQueuePage(self, value: int) -> None: set_queue_page(self, value)
    @Slot(int)
    def setQueuePageSize(self, value: int) -> None: set_queue_page_size(self, value)
    @Slot(str)
    def setQueueSearchText(self, value: str) -> None: set_queue_search_text(self, value)
    @Slot(str)
    def setQueueProject(self, value: str) -> None: set_queue_project(self, value)
    @Slot(str)
    def setQueueResource(self, value: str) -> None: set_queue_resource(self, value)
    @Slot(str, str)
    def setQueuePeriodRange(self, start: str, end: str) -> None: set_queue_period_range(self, start, end)
    @Slot(str, int)
    def setQueueSort(self, key: str, direction: int) -> None: set_queue_sort(self, key, direction)

    @Slot("QVariantMap", result="QVariantMap")
    def approvePeriod(self, payload): return self._mutations.approve_period(payload)
    @Slot("QVariantMap", result="QVariantMap")
    def rejectPeriod(self, payload): return self._mutations.reject_period(payload)
    @Slot("QVariantMap", result="QVariantMap")
    def lockPeriod(self, payload): return self._mutations.lock_period(payload)
    @Slot("QVariantMap", result="QVariantMap")
    def unlockPeriod(self, payload): return self._mutations.unlock_period(payload)

    def _set_overview(self, v): _setters.set_overview(self, v)
    def _set_project_options(self, v): _setters.set_project_options(self, v)
    def _set_queue_status_options(self, v): _setters.set_queue_status_options(self, v)
    def _set_queue_resource_options(self, v): _setters.set_queue_resource_options(self, v)
    def _set_selected_queue_status(self, v): _setters.set_selected_queue_status(self, v)
    def _set_selected_queue_period_id(self, v): _setters.set_selected_queue_period_id(self, v)
    def _set_review_queue(self, v): _setters.set_review_queue(self, v)
    def _set_review_detail(self, v): _setters.set_review_detail(self, v)
    def _set_queue_page(self, v): _setters.set_queue_page(self, v)
    def _set_queue_page_size(self, v): _setters.set_queue_page_size(self, v)
    def _set_queue_total_count(self, v): _setters.set_queue_total_count(self, v)
    def _set_queue_search_text(self, v): _setters.set_queue_search_text(self, v)
    def _set_selected_queue_project_id(self, v): _setters.set_selected_queue_project_id(self, v)
    def _set_selected_queue_resource_id(self, v): _setters.set_selected_queue_resource_id(self, v)
    def _set_queue_period_start_from(self, v): _setters.set_queue_period_start_from(self, v)
    def _set_queue_period_start_to(self, v): _setters.set_queue_period_start_to(self, v)
    def _set_queue_sort_key(self, v): _setters.set_queue_sort_key(self, v)
    def _set_queue_sort_direction(self, v): _setters.set_queue_sort_direction(self, v)


__all__ = ["ProjectManagementTimesheetsWorkspaceController"]
