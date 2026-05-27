from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_financials_collection_view_model,
    serialize_financials_commitment_summary_view_model,
    serialize_financials_detail_view_model,
    serialize_financials_forecast_view_model,
    serialize_financials_overview_view_model,
    serialize_financials_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectFinancialsWorkspacePresenter,
    ProjectManagementWorkspacePresenter,
)

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementFinancialsWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    costTypeOptionsChanged = Signal()
    taskOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    selectedCostTypeChanged = Signal()
    searchTextChanged = Signal()
    costsChanged = Signal()
    selectedCostChanged = Signal()
    selectedCostIdChanged = Signal()
    cashflowChanged = Signal()
    ledgerChanged = Signal()
    sourceAnalyticsChanged = Signal()
    costTypeAnalyticsChanged = Signal()
    notesChanged = Signal()
    costPageChanged = Signal()
    costPageSizeChanged = Signal()
    costTotalCountChanged = Signal()
    selectedCostIdsChanged = Signal()
    selectedCostCountChanged = Signal()
    forecastChanged = Signal()
    commitmentSummaryChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        financials_workspace_presenter: ProjectFinancialsWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.financials"
        )
        self._financials_workspace_presenter = (
            financials_workspace_presenter or ProjectFinancialsWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._project_options: list[dict[str, object]] = []
        self._cost_type_options: list[dict[str, object]] = []
        self._task_options: list[dict[str, object]] = []
        self._selected_project_id = ""
        self._selected_cost_type = "all"
        self._search_text = ""
        self._costs: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_cost: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._selected_cost_id = ""
        self._cashflow: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._ledger: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._source_analytics: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._cost_type_analytics: dict[str, object] = {"title": "", "subtitle": "", "emptyState": "", "items": []}
        self._notes: list[str] = []
        self._cost_page = 1
        self._cost_page_size = 25
        self._cost_total_count = 0
        self._selected_cost_ids: list[str] = []
        self._forecast: dict[str, object] = {
            "method": "", "methodLabel": "", "bacLabel": "", "acLabel": "", "evLabel": "",
            "etcLabel": "", "eacLabel": "", "vacLabel": "", "cpiLabel": "",
            "isOverBudget": False, "exceedsThreshold": False, "thresholdPercent": 10.0,
            "alertMessage": "", "metrics": [],
        }
        self._commitment_summary: dict[str, object] = {
            "plannedLabel": "", "uncommittedLabel": "", "committedLabel": "",
            "invoicedLabel": "", "paidLabel": "", "exposureLabel": "", "commitmentRatePct": 0.0,
        }
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> list[dict[str, object]]:
        return self._project_options

    @Property("QVariantList", notify=costTypeOptionsChanged)
    def costTypeOptions(self) -> list[dict[str, object]]:
        return self._cost_type_options

    @Property("QVariantList", notify=taskOptionsChanged)
    def taskOptions(self) -> list[dict[str, object]]:
        return self._task_options

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str:
        return self._selected_project_id

    @Property(str, notify=selectedCostTypeChanged)
    def selectedCostType(self) -> str:
        return self._selected_cost_type

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=costsChanged)
    def costs(self) -> dict[str, object]:
        return self._costs

    @Property("QVariantMap", notify=selectedCostChanged)
    def selectedCost(self) -> dict[str, object]:
        return self._selected_cost

    @Property(str, notify=selectedCostIdChanged)
    def selectedCostId(self) -> str:
        return self._selected_cost_id

    @Property("QVariantMap", notify=cashflowChanged)
    def cashflow(self) -> dict[str, object]:
        return self._cashflow

    @Property("QVariantMap", notify=ledgerChanged)
    def ledger(self) -> dict[str, object]:
        return self._ledger

    @Property("QVariantMap", notify=sourceAnalyticsChanged)
    def sourceAnalytics(self) -> dict[str, object]:
        return self._source_analytics

    @Property("QVariantMap", notify=costTypeAnalyticsChanged)
    def costTypeAnalytics(self) -> dict[str, object]:
        return self._cost_type_analytics

    @Property("QVariantList", notify=notesChanged)
    def notes(self) -> list[str]:
        return self._notes

    @Property("QVariantMap", notify=forecastChanged)
    def forecast(self) -> dict[str, object]:
        return self._forecast

    @Property("QVariantMap", notify=commitmentSummaryChanged)
    def commitmentSummary(self) -> dict[str, object]:
        return self._commitment_summary

    @Property("QVariantList", notify=costTypeOptionsChanged)
    def bulkCostTypeOptions(self) -> list[dict[str, object]]:
        return [o for o in self._cost_type_options if str(o.get("value", "")).lower() != "all"]

    @Property(int, notify=costPageChanged)
    def costPage(self) -> int:
        return self._cost_page

    @Property(int, notify=costPageSizeChanged)
    def costPageSize(self) -> int:
        return self._cost_page_size

    @Property(int, notify=costTotalCountChanged)
    def costTotalCount(self) -> int:
        return self._cost_total_count

    @Property("QVariantList", notify=selectedCostIdsChanged)
    def selectedCostIds(self) -> list[str]:
        return self._selected_cost_ids

    @Property(int, notify=selectedCostCountChanged)
    def selectedCostCount(self) -> int:
        return len(self._selected_cost_ids)

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
            workspace_state = self._financials_workspace_presenter.build_workspace_state(
                selected_project_id=self._selected_project_id or None,
                selected_cost_type=self._selected_cost_type,
                search_text=self._search_text,
                selected_cost_id=self._selected_cost_id or None,
            )
            self._set_overview(
                serialize_financials_overview_view_model(workspace_state.overview)
            )
            self._set_project_options(
                serialize_selector_options(workspace_state.project_options)
            )
            self._set_cost_type_options(
                serialize_selector_options(workspace_state.cost_type_options)
            )
            self._set_task_options(
                serialize_selector_options(workspace_state.task_options)
            )
            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_selected_cost_type(workspace_state.selected_cost_type)
            self._set_search_text(workspace_state.search_text)
            self._set_costs(
                serialize_financials_collection_view_model(workspace_state.costs)
            )
            self._set_cost_total_count(len(self._costs.get("items") or []))
            self._set_selected_cost_id(workspace_state.selected_cost_id)
            self._set_selected_cost(
                serialize_financials_detail_view_model(
                    workspace_state.selected_cost_detail
                )
            )
            self._set_cashflow(
                serialize_financials_collection_view_model(workspace_state.cashflow)
            )
            self._set_ledger(
                serialize_financials_collection_view_model(workspace_state.ledger)
            )
            self._set_source_analytics(
                serialize_financials_collection_view_model(
                    workspace_state.source_analytics
                )
            )
            self._set_cost_type_analytics(
                serialize_financials_collection_view_model(
                    workspace_state.cost_type_analytics
                )
            )
            self._set_notes(list(workspace_state.notes))
            self._set_empty_state(workspace_state.empty_state)
            self._set_forecast(
                serialize_financials_forecast_view_model(workspace_state.forecast)
            )
            self._set_commitment_summary(
                serialize_financials_commitment_summary_view_model(workspace_state.commitment_summary)
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        normalized_value = (project_id or "").strip()
        if normalized_value == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_value)
        self._set_selected_cost_id("")
        self.refresh()

    @Slot(str)
    def setCostTypeFilter(self, cost_type: str) -> None:
        normalized_value = (cost_type or "all").strip()
        if normalized_value == self._selected_cost_type:
            return
        self._set_selected_cost_type(normalized_value)
        self.refresh()

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized_value = (search_text or "").strip()
        if normalized_value == self._search_text:
            return
        self._set_search_text(normalized_value)
        self.refresh()

    @Slot(str)
    def selectCost(self, cost_id: str) -> None:
        normalized_value = (cost_id or "").strip()
        if normalized_value == self._selected_cost_id:
            return
        self._set_selected_cost_id(normalized_value)
        self.refresh()

    @Slot(str, result="QVariantMap")
    def computeForecast(self, method: str) -> dict[str, object]:
        normalized = (method or "bac_over_cpi").strip().lower()
        return run_mutation(
            operation=lambda: self._apply_forecast(normalized),
            success_message="Forecast recalculated.",
            on_success=lambda: None,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _apply_forecast(self, method: str) -> None:
        forecast_dto = self._financials_workspace_presenter._desktop_api.get_cost_forecast(
            self._selected_project_id, method=method
        )
        from src.ui_qml.modules.project_management.view_models.financials import FinancialsForecastViewModel
        vm = self._financials_workspace_presenter._build_forecast_view_model(forecast_dto)
        self._set_forecast(serialize_financials_forecast_view_model(vm))

    @Slot()
    def exportFinancials(self) -> None:
        self._set_feedback_message(
            "Export is not yet available. Use Reports to generate financial summaries."
        )

    @Slot(int)
    def setCostPage(self, page: int) -> None:
        p = max(1, page)
        if p == self._cost_page:
            return
        self._set_cost_page(p)
        self.refresh()

    @Slot(int)
    def setCostPageSize(self, page_size: int) -> None:
        if page_size <= 0 or page_size == self._cost_page_size:
            return
        self._cost_page_size = page_size
        self.costPageSizeChanged.emit()
        self._set_cost_page(1)
        self.refresh()

    @Slot(str, bool)
    def setCostBulkSelection(self, cost_id: str, selected: bool) -> None:
        ids = list(self._selected_cost_ids)
        if selected:
            if cost_id not in ids:
                ids.append(cost_id)
        else:
            ids = [i for i in ids if i != cost_id]
        self._set_selected_cost_ids(ids)

    @Slot()
    def selectVisibleCosts(self) -> None:
        ids = [
            str(item.get("id", ""))
            for item in (self._costs.get("items") or [])
            if item.get("id")
        ]
        self._set_selected_cost_ids(ids)

    @Slot()
    def clearCostBulkSelection(self) -> None:
        self._set_selected_cost_ids([])

    @Slot("QVariantList", result="QVariantMap")
    def bulkDeleteCosts(self, cost_ids: list) -> dict[str, object]:
        ids = [str(i) for i in (cost_ids or [])]
        if not ids:
            return {"ok": False, "message": "No cost items selected."}
        return run_mutation(
            operation=lambda: [
                self._financials_workspace_presenter.delete_cost_item(i) for i in ids
            ],
            success_message=f"{len(ids)} cost item(s) deleted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkCostType(self, payload: dict[str, object]) -> dict[str, object]:
        ids = list(self._selected_cost_ids)
        cost_type = str(payload.get("value") or payload.get("costType") or "")
        if not ids or not cost_type:
            return {"ok": False, "message": "No items or cost type selected."}
        return run_mutation(
            operation=lambda: [
                self._financials_workspace_presenter.update_cost_item(
                    {"id": i, "costType": cost_type}
                )
                for i in ids
            ],
            success_message=f"Cost type updated for {len(ids)} item(s).",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createCostItem(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.create_cost_item(
                dict(payload)
            ),
            success_message="Cost item created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateCostItem(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.update_cost_item(
                dict(payload)
            ),
            success_message="Cost item updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteCostItem(self, cost_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._financials_workspace_presenter.delete_cost_item(
                cost_id
            ),
            success_message="Cost item deleted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "project_tasks",
            "project_costs",
            scope_code="project_management",
        )

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_project_options(self, project_options: list[dict[str, object]]) -> None:
        if project_options == self._project_options:
            return
        self._project_options = project_options
        self.projectOptionsChanged.emit()

    def _set_cost_type_options(self, cost_type_options: list[dict[str, object]]) -> None:
        if cost_type_options == self._cost_type_options:
            return
        self._cost_type_options = cost_type_options
        self.costTypeOptionsChanged.emit()

    def _set_task_options(self, task_options: list[dict[str, object]]) -> None:
        if task_options == self._task_options:
            return
        self._task_options = task_options
        self.taskOptionsChanged.emit()

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()

    def _set_selected_cost_type(self, selected_cost_type: str) -> None:
        if selected_cost_type == self._selected_cost_type:
            return
        self._selected_cost_type = selected_cost_type
        self.selectedCostTypeChanged.emit()

    def _set_search_text(self, search_text: str) -> None:
        if search_text == self._search_text:
            return
        self._search_text = search_text
        self.searchTextChanged.emit()

    def _set_costs(self, costs: dict[str, object]) -> None:
        if costs == self._costs:
            return
        self._costs = costs
        self.costsChanged.emit()

    def _set_selected_cost(self, selected_cost: dict[str, object]) -> None:
        if selected_cost == self._selected_cost:
            return
        self._selected_cost = selected_cost
        self.selectedCostChanged.emit()

    def _set_selected_cost_id(self, selected_cost_id: str) -> None:
        if selected_cost_id == self._selected_cost_id:
            return
        self._selected_cost_id = selected_cost_id
        self.selectedCostIdChanged.emit()

    def _set_cashflow(self, cashflow: dict[str, object]) -> None:
        if cashflow == self._cashflow:
            return
        self._cashflow = cashflow
        self.cashflowChanged.emit()

    def _set_ledger(self, ledger: dict[str, object]) -> None:
        if ledger == self._ledger:
            return
        self._ledger = ledger
        self.ledgerChanged.emit()

    def _set_source_analytics(self, source_analytics: dict[str, object]) -> None:
        if source_analytics == self._source_analytics:
            return
        self._source_analytics = source_analytics
        self.sourceAnalyticsChanged.emit()

    def _set_cost_type_analytics(self, cost_type_analytics: dict[str, object]) -> None:
        if cost_type_analytics == self._cost_type_analytics:
            return
        self._cost_type_analytics = cost_type_analytics
        self.costTypeAnalyticsChanged.emit()

    def _set_notes(self, notes: list[str]) -> None:
        if notes == self._notes:
            return
        self._notes = notes
        self.notesChanged.emit()

    def _set_cost_page(self, v: int) -> None:
        if v == self._cost_page:
            return
        self._cost_page = v
        self.costPageChanged.emit()

    def _set_cost_total_count(self, v: int) -> None:
        if v == self._cost_total_count:
            return
        self._cost_total_count = v
        self.costTotalCountChanged.emit()

    def _set_selected_cost_ids(self, ids: list[str]) -> None:
        if ids == self._selected_cost_ids:
            return
        self._selected_cost_ids = ids
        self.selectedCostIdsChanged.emit()
        self.selectedCostCountChanged.emit()

    def _set_forecast(self, forecast: dict[str, object]) -> None:
        if forecast == self._forecast:
            return
        self._forecast = forecast
        self.forecastChanged.emit()

    def _set_commitment_summary(self, summary: dict[str, object]) -> None:
        if summary == self._commitment_summary:
            return
        self._commitment_summary = summary
        self.commitmentSummaryChanged.emit()


__all__ = ["ProjectManagementFinancialsWorkspaceController"]
