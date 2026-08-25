from __future__ import annotations

import calendar
from datetime import date

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
)
from src.ui_qml.modules.project_management.controllers.common.mutation_runner import (
    run_mutation,
)
from src.ui_qml.modules.project_management.presenters.owner_timesheets import (
    OwnerTimesheetsPresenter,
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
class ProjectManagementOwnerTimesheetsController(ProjectManagementWorkspaceControllerBase):
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

    def __init__(
        self,
        *,
        presenter: OwnerTimesheetsPresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter or OwnerTimesheetsPresenter()
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
        self._subscribe_domain_change(
            "timesheet_period",
            "project_tasks",
            "resource",
            scope_code="project_management",
        )
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
            self._entry_model.set_rows([])
            self._history_model.set_rows([])
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    def _reset_entry_page_and_refresh(self) -> None:
        self._assign("_entry_page", 1, self.entryPageChanged)
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
        return run_mutation(
            operation=lambda: self._presenter.save_entry(command_payload),
            success_message=("Time entry updated." if command_payload.get("entryId") else "Time entry added."),
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteEntry(self, entry_id: str):
        return run_mutation(
            operation=lambda: self._presenter.delete_entry(
                entry_id,
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


__all__ = ["ProjectManagementOwnerTimesheetsController"]
