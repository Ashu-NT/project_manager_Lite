from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_financials_collection_view_model,
    serialize_financials_detail_view_model,
    serialize_financials_overview_view_model,
    serialize_financials_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectFinancialsWorkspacePresenter,
    ProjectManagementWorkspacePresenter,
)


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


__all__ = ["ProjectManagementFinancialsWorkspaceController"]
