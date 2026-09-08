from __future__ import annotations

import calendar
from datetime import date

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
)
from src.ui_qml.modules.project_management.controllers.common.mutation_runner import (
    run_mutation,
)
from src.ui_qml.modules.project_management.presenters.resource_timesheets import (
    ResourceTimesheetsPresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _shift_month(value: date, offset: int) -> date:
    month_index = value.year * 12 + value.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


@QmlElement
@QmlUncreatable("Owner timesheets controller is provided by the PM catalog.")
class ProjectManagementResourceTimesheetsController(ProjectManagementWorkspaceControllerBase):
    periodChanged = Signal()
    entriesChanged = Signal()
    entryPageChanged = Signal()
    entryPageSizeChanged = Signal()
    entryTotalChanged = Signal()
    entrySearchTextChanged = Signal()
    selectedProjectIdChanged = Signal()
    selectedTaskIdChanged = Signal()
    entrySortKeyChanged = Signal()
    entrySortDirectionChanged = Signal()
    assignmentOptionsChanged = Signal()
    projectOptionsChanged = Signal()
    historyChanged = Signal()
    historyPageChanged = Signal()
    historyPageSizeChanged = Signal()
    historyTotalChanged = Signal()
    selectedPeriodStartChanged = Signal()
    selectedScopeChanged = Signal()
    scopeOptionsChanged = Signal()
    canSelectScopeChanged = Signal()
    canSelectResourceChanged = Signal()
    selectedResourceIdChanged = Signal()
    resourceSearchTextChanged = Signal()
    resourceOptionsChanged = Signal()
    resourcePageChanged = Signal()
    resourcePageSizeChanged = Signal()
    resourceTotalChanged = Signal()

    def __init__(
        self,
        *,
        presenter: ResourceTimesheetsPresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter or ResourceTimesheetsPresenter()
        self._set_workspace(
            {
                "routeId": "project_management.timesheets",
                "title": "Timesheets",
                "summary": "Review, correct, and submit your monthly time.",
            }
        )
        self._period: dict[str, object] = {}
        self._entries: list[dict[str, object]] = []
        self._entry_model = DynamicTableModel(self)
        self._entry_page = 1
        self._entry_page_size = 25
        self._entry_total = 0
        self._entry_search_text = ""
        self._selected_project_id = "all"
        self._selected_task_id = "all"
        self._entry_sort_key = "date"
        self._entry_sort_direction = 1
        self._assignment_options: list[dict[str, object]] = []
        self._project_options: list[dict[str, object]] = []
        self._history: list[dict[str, object]] = []
        self._history_model = DynamicTableModel(self)
        self._history_page = 1
        self._history_page_size = 12
        self._history_total = 0
        self._selected_period_start = _month_start(date.today())
        self._selected_scope = "mine"
        self._scope_options: list[dict[str, object]] = []
        self._can_select_scope = False
        self._can_select_resource = False
        self._selected_resource_id = ""
        self._resource_search_text = ""
        self._resource_options: list[dict[str, object]] = []
        self._resource_page = 1
        self._resource_page_size = 20
        self._resource_total = 0
        for signal in (
            domain_events.tasks_changed,
        ):
            self._subscribe_domain_signal(signal, lambda _payload: self._request_domain_refresh())
        self.refresh()

    period = Property("QVariantMap", lambda self: self._period, notify=periodChanged)
    entries = Property("QVariantList", lambda self: self._entries, notify=entriesChanged)
    entryTableModel = Property(QObject, lambda self: self._entry_model, constant=True)
    entryPage = Property(int, lambda self: self._entry_page, notify=entryPageChanged)
    entryPageSize = Property(int, lambda self: self._entry_page_size, notify=entryPageSizeChanged)
    entryTotal = Property(int, lambda self: self._entry_total, notify=entryTotalChanged)
    entrySearchText = Property(str, lambda self: self._entry_search_text, notify=entrySearchTextChanged)
    selectedProjectId = Property(str, lambda self: self._selected_project_id, notify=selectedProjectIdChanged)
    selectedTaskId = Property(str, lambda self: self._selected_task_id, notify=selectedTaskIdChanged)
    entrySortKey = Property(str, lambda self: self._entry_sort_key, notify=entrySortKeyChanged)
    entrySortDirection = Property(int, lambda self: self._entry_sort_direction, notify=entrySortDirectionChanged)
    assignmentOptions = Property("QVariantList", lambda self: self._assignment_options, notify=assignmentOptionsChanged)
    projectOptions = Property("QVariantList", lambda self: self._project_options, notify=projectOptionsChanged)
    history = Property("QVariantList", lambda self: self._history, notify=historyChanged)
    historyTableModel = Property(QObject, lambda self: self._history_model, constant=True)
    historyPage = Property(int, lambda self: self._history_page, notify=historyPageChanged)
    historyPageSize = Property(int, lambda self: self._history_page_size, notify=historyPageSizeChanged)
    historyTotal = Property(int, lambda self: self._history_total, notify=historyTotalChanged)
    selectedPeriodStart = Property(
        str,
        lambda self: self._selected_period_start.isoformat(),
        notify=selectedPeriodStartChanged,
    )
    selectedScope = Property(str, lambda self: self._selected_scope, notify=selectedScopeChanged)
    scopeOptions = Property("QVariantList", lambda self: self._scope_options, notify=scopeOptionsChanged)
    canSelectScope = Property(bool, lambda self: self._can_select_scope, notify=canSelectScopeChanged)
    canSelectResource = Property(bool, lambda self: self._can_select_resource, notify=canSelectResourceChanged)
    selectedResourceId = Property(str, lambda self: self._selected_resource_id, notify=selectedResourceIdChanged)
    resourceSearchText = Property(str, lambda self: self._resource_search_text, notify=resourceSearchTextChanged)
    resourceOptions = Property("QVariantList", lambda self: self._resource_options, notify=resourceOptionsChanged)
    resourcePage = Property(int, lambda self: self._resource_page, notify=resourcePageChanged)
    resourcePageSize = Property(int, lambda self: self._resource_page_size, notify=resourcePageSizeChanged)
    resourceTotal = Property(int, lambda self: self._resource_total, notify=resourceTotalChanged)

    def _assign(self, name: str, value, signal: Signal) -> None:
        if getattr(self, name) == value:
            return
        setattr(self, name, value)
        signal.emit()

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            state = self._presenter.build_state(
                scope=self._selected_scope,
                resource_id=self._selected_resource_id,
                resource_search_text=self._resource_search_text,
                resource_page=self._resource_page,
                resource_page_size=self._resource_page_size,
                period_start=self._selected_period_start,
                search_text=self._entry_search_text,
                project_id=self._selected_project_id,
                task_id=self._selected_task_id,
                page=self._entry_page,
                page_size=self._entry_page_size,
                sort_key=self._entry_sort_key,
                sort_direction="desc" if self._entry_sort_direction else "asc",
                history_page=self._history_page,
                history_page_size=self._history_page_size,
            )
            self._set_workspace(state["workspace"])
            self._assign("_selected_scope", state["selectedScope"], self.selectedScopeChanged)
            self._assign("_scope_options", state["scopeOptions"], self.scopeOptionsChanged)
            self._assign("_can_select_scope", state["canSelectScope"], self.canSelectScopeChanged)
            self._assign("_can_select_resource", state["canSelectResource"], self.canSelectResourceChanged)
            self._assign("_selected_resource_id", state["selectedResourceId"], self.selectedResourceIdChanged)
            self._assign("_resource_options", state["resourceOptions"], self.resourceOptionsChanged)
            self._assign("_resource_total", state["resourceTotal"], self.resourceTotalChanged)
            self._assign("_resource_page", state["resourcePage"], self.resourcePageChanged)
            self._assign("_resource_page_size", state["resourcePageSize"], self.resourcePageSizeChanged)
            self._assign("_period", state["period"], self.periodChanged)
            self._assign("_entries", state["entries"], self.entriesChanged)
            self._entry_model.set_rows(state["entries"])
            self._assign("_entry_total", state["entryTotal"], self.entryTotalChanged)
            self._assign("_entry_page", state["entryPage"], self.entryPageChanged)
            self._assign("_entry_page_size", state["entryPageSize"], self.entryPageSizeChanged)
            self._assign("_entry_sort_key", state["entrySortKey"], self.entrySortKeyChanged)
            self._assign(
                "_entry_sort_direction",
                1 if state["entrySortDirection"] == "desc" else 0,
                self.entrySortDirectionChanged,
            )
            self._assign("_assignment_options", state["assignmentOptions"], self.assignmentOptionsChanged)
            self._assign("_project_options", state["projectOptions"], self.projectOptionsChanged)
            self._assign("_history", state["history"], self.historyChanged)
            self._history_model.set_rows(state["history"])
            self._assign("_history_total", state["historyTotal"], self.historyTotalChanged)
            self._assign("_history_page", state["historyPage"], self.historyPageChanged)
            self._assign("_history_page_size", state["historyPageSize"], self.historyPageSizeChanged)
        except Exception as exc:
            self._assign("_period", {}, self.periodChanged)
            self._assign("_entries", [], self.entriesChanged)
            self._assign("_entry_total", 0, self.entryTotalChanged)
            self._assign("_assignment_options", [], self.assignmentOptionsChanged)
            self._assign("_project_options", [], self.projectOptionsChanged)
            self._assign("_history", [], self.historyChanged)
            self._assign("_history_total", 0, self.historyTotalChanged)
            self._entry_model.set_rows([])
            self._history_model.set_rows([])
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    def _reset_entry_page_and_refresh(self) -> None:
        self._assign("_entry_page", 1, self.entryPageChanged)
        self.refresh()

    @Slot(str)
    def setTimesheetScope(self, value: str) -> None:
        normalized = str(value or "").strip().lower()
        if not normalized or normalized == self._selected_scope:
            return
        self._assign("_selected_scope", normalized, self.selectedScopeChanged)
        self._assign("_selected_resource_id", "", self.selectedResourceIdChanged)
        self._assign("_resource_search_text", "", self.resourceSearchTextChanged)
        self._assign("_resource_page", 1, self.resourcePageChanged)
        self._assign("_entry_page", 1, self.entryPageChanged)
        self.refresh()

    @Slot(str)
    def selectTimesheetResource(self, value: str) -> None:
        normalized = str(value or "").strip()
        if normalized == self._selected_resource_id:
            return
        self._assign("_selected_resource_id", normalized, self.selectedResourceIdChanged)
        self._assign("_entry_page", 1, self.entryPageChanged)
        self._assign("_history_page", 1, self.historyPageChanged)
        self.refresh()

    @Slot(str)
    def setResourceSearchText(self, value: str) -> None:
        normalized = str(value or "").strip()
        if normalized == self._resource_search_text:
            return
        self._assign("_resource_search_text", normalized, self.resourceSearchTextChanged)
        self._assign("_resource_page", 1, self.resourcePageChanged)
        self.refresh()

    @Slot(int)
    def setResourcePage(self, value: int) -> None:
        normalized = max(1, int(value))
        if normalized == self._resource_page:
            return
        self._assign("_resource_page", normalized, self.resourcePageChanged)
        self.refresh()

    @Slot(int)
    def shiftPeriod(self, offset: int) -> None:
        target = _shift_month(self._selected_period_start, int(offset))
        if target > _month_start(date.today()):
            return
        self._selected_period_start = target
        self.selectedPeriodStartChanged.emit()
        self._assign("_entry_page", 1, self.entryPageChanged)
        self.refresh()

    @Slot()
    def selectCurrentPeriod(self) -> None:
        target = _month_start(date.today())
        if target == self._selected_period_start:
            return
        self._selected_period_start = target
        self.selectedPeriodStartChanged.emit()
        self._reset_entry_page_and_refresh()

    @Slot(str)
    def selectPeriod(self, value: str) -> None:
        target = _month_start(date.fromisoformat(str(value or "").strip()))
        if target > _month_start(date.today()) or target == self._selected_period_start:
            return
        self._selected_period_start = target
        self.selectedPeriodStartChanged.emit()
        self._reset_entry_page_and_refresh()

    @Slot(int)
    def setEntryPage(self, value: int) -> None:
        value = max(1, int(value))
        if value == self._entry_page:
            return
        self._assign("_entry_page", value, self.entryPageChanged)
        self.refresh()

    @Slot(int)
    def setEntryPageSize(self, value: int) -> None:
        value = max(1, int(value))
        if value == self._entry_page_size:
            return
        self._assign("_entry_page_size", value, self.entryPageSizeChanged)
        self._reset_entry_page_and_refresh()

    @Slot(str)
    def setEntrySearchText(self, value: str) -> None:
        value = str(value or "").strip()
        if value == self._entry_search_text:
            return
        self._assign("_entry_search_text", value, self.entrySearchTextChanged)
        self._reset_entry_page_and_refresh()

    @Slot(str)
    def setProjectFilter(self, value: str) -> None:
        value = str(value or "").strip() or "all"
        if value == self._selected_project_id:
            return
        self._assign("_selected_project_id", value, self.selectedProjectIdChanged)
        self._reset_entry_page_and_refresh()

    @Slot(str, int)
    def setEntrySort(self, key: str, direction: int) -> None:
        self._assign("_entry_sort_key", str(key or "").strip(), self.entrySortKeyChanged)
        self._assign("_entry_sort_direction", 1 if int(direction) else 0, self.entrySortDirectionChanged)
        self._reset_entry_page_and_refresh()

    @Slot(int)
    def setHistoryPage(self, value: int) -> None:
        value = max(1, int(value))
        if value == self._history_page:
            return
        self._assign("_history_page", value, self.historyPageChanged)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def saveEntry(self, payload):
        command_payload = dict(payload or {})
        command_payload["periodStart"] = self._selected_period_start.isoformat()
        command_payload["scope"] = self._selected_scope
        command_payload["resourceId"] = self._selected_resource_id
        return run_mutation(
            operation=lambda: self._presenter.save_entry(command_payload),
            success_message=("Time entry updated." if command_payload.get("entryId") else "Time entry added."),
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, int, result="QVariantMap")
    def deleteEntry(self, entry_id: str, expected_version: int):
        return run_mutation(
            operation=lambda: self._presenter.delete_entry(
                entry_id,
                expected_version=expected_version,
                scope=self._selected_scope,
                resource_id=self._selected_resource_id or None,
                period_start=self._selected_period_start,
            ),
            success_message="Time entry deleted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def submitPeriod(self, note: str):
        version = int(self._period.get("version", 0) or 0)
        return run_mutation(
            operation=lambda: self._presenter.submit_period(
                scope=self._selected_scope,
                resource_id=self._selected_resource_id or None,
                period_start=self._selected_period_start,
                expected_version=version,
                note=str(note or "").strip(),
            ),
            success_message=(
                "Timesheet resubmitted for review."
                if self._period.get("status") == "REJECTED"
                else "Timesheet submitted for review."
            ),
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )


__all__ = ["ProjectManagementResourceTimesheetsController"]
