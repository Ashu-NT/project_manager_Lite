from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
)
from src.ui_qml.modules.project_management.controllers.financials.financials_mutation_mixin import FinancialsMutationMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_refresh_mixin import FinancialsRefreshMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_selection_mixin import FinancialsSelectionMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_state_mixin import FinancialsStateMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_table_mixin import FinancialsTableMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_types import (
    FinancialsMap,
    FinancialsObjectList,
    default_collection,
    default_commitment_summary,
    default_forecast,
    default_overview,
    default_selected_cost,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectFinancialsWorkspacePresenter,
    ProjectManagementWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementFinancialsWorkspaceController(
    ProjectManagementWorkspaceControllerBase,
    FinancialsRefreshMixin,
    FinancialsSelectionMixin,
    FinancialsTableMixin,
    FinancialsMutationMixin,
    FinancialsStateMixin,
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
    baselineVarianceChanged = Signal()

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
        self._overview = default_overview()
        self._project_options: FinancialsObjectList = []
        self._cost_type_options: FinancialsObjectList = []
        self._task_options: FinancialsObjectList = []
        self._selected_project_id = ""
        self._selected_cost_type = "all"
        self._search_text = ""
        self._costs_table_model = DynamicTableModel(self)
        self._ledger_table_model = DynamicTableModel(self)
        self._costs = default_collection()
        self._selected_cost = default_selected_cost()
        self._selected_cost_id = ""
        self._cashflow = default_collection()
        self._ledger = default_collection()
        self._source_analytics = default_collection()
        self._cost_type_analytics = default_collection()
        self._notes: list[str] = []
        self._cost_page = 1
        self._cost_page_size = 25
        self._cost_total_count = 0
        self._selected_cost_ids: list[str] = []
        self._forecast = default_forecast()
        self._commitment_summary = default_commitment_summary()
        self._baseline_variance: FinancialsObjectList = []
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> FinancialsMap: return self._overview

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> FinancialsObjectList: return self._project_options

    @Property("QVariantList", notify=costTypeOptionsChanged)
    def costTypeOptions(self) -> FinancialsObjectList: return self._cost_type_options

    @Property("QVariantList", notify=taskOptionsChanged)
    def taskOptions(self) -> FinancialsObjectList: return self._task_options

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str: return self._selected_project_id

    @Property(str, notify=selectedCostTypeChanged)
    def selectedCostType(self) -> str: return self._selected_cost_type

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str: return self._search_text

    @Property("QVariantMap", notify=costsChanged)
    def costs(self) -> FinancialsMap: return self._costs

    @Property("QVariantMap", notify=selectedCostChanged)
    def selectedCost(self) -> FinancialsMap: return self._selected_cost

    @Property(str, notify=selectedCostIdChanged)
    def selectedCostId(self) -> str: return self._selected_cost_id

    @Property("QVariantMap", notify=cashflowChanged)
    def cashflow(self) -> FinancialsMap: return self._cashflow

    @Property("QVariantMap", notify=ledgerChanged)
    def ledger(self) -> FinancialsMap: return self._ledger

    @Property(QObject, constant=True)
    def costsTableModel(self) -> DynamicTableModel: return self._costs_table_model

    @Property(QObject, constant=True)
    def ledgerTableModel(self) -> DynamicTableModel: return self._ledger_table_model

    @Property("QVariantMap", notify=sourceAnalyticsChanged)
    def sourceAnalytics(self) -> FinancialsMap: return self._source_analytics

    @Property("QVariantMap", notify=costTypeAnalyticsChanged)
    def costTypeAnalytics(self) -> FinancialsMap: return self._cost_type_analytics

    @Property("QVariantList", notify=notesChanged)
    def notes(self) -> list[str]: return self._notes

    @Property("QVariantMap", notify=forecastChanged)
    def forecast(self) -> FinancialsMap: return self._forecast

    @Property("QVariantMap", notify=commitmentSummaryChanged)
    def commitmentSummary(self) -> FinancialsMap: return self._commitment_summary

    @Property("QVariantList", notify=baselineVarianceChanged)
    def baselineVariance(self) -> FinancialsObjectList: return self._baseline_variance

    @Property("QVariantList", notify=costTypeOptionsChanged)
    def bulkCostTypeOptions(self) -> FinancialsObjectList:
        return [o for o in self._cost_type_options if str(o.get("value", "")).lower() != "all"]

    @Property(int, notify=costPageChanged)
    def costPage(self) -> int: return self._cost_page

    @Property(int, notify=costPageSizeChanged)
    def costPageSize(self) -> int: return self._cost_page_size

    @Property(int, notify=costTotalCountChanged)
    def costTotalCount(self) -> int: return self._cost_total_count

    @Property("QVariantList", notify=selectedCostIdsChanged)
    def selectedCostIds(self) -> list[str]: return self._selected_cost_ids

    @Property(int, notify=selectedCostCountChanged)
    def selectedCostCount(self) -> int: return len(self._selected_cost_ids)

    @Slot()
    def refresh(self) -> None: self._refresh()

    @Slot(str)
    def selectProject(self, project_id: str) -> None: self._select_project(project_id)

    @Slot(str)
    def setCostTypeFilter(self, cost_type: str) -> None: self._set_cost_type_filter(cost_type)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None: self._set_search_text_from_qml(search_text)

    @Slot(str)
    def selectCost(self, cost_id: str) -> None: self._select_cost(cost_id)

    @Slot(str, result="QVariantMap")
    def computeForecast(self, method: str) -> FinancialsMap: return self._compute_forecast(method)

    @Slot()
    def exportFinancials(self) -> None: self._export_financials()

    @Slot(int)
    def setCostPage(self, page: int) -> None: self._set_cost_page_from_qml(page)

    @Slot(int)
    def setCostPageSize(self, page_size: int) -> None: self._set_cost_page_size_from_qml(page_size)

    @Slot(str, bool)
    def setCostBulkSelection(self, cost_id: str, selected: bool) -> None: self._set_cost_bulk_selection(cost_id, selected)

    @Slot()
    def selectVisibleCosts(self) -> None: self._select_visible_costs()

    @Slot()
    def clearCostBulkSelection(self) -> None: self._clear_cost_bulk_selection()

    @Slot("QVariantList", result="QVariantMap")
    def bulkDeleteCosts(self, cost_ids: list) -> FinancialsMap: return self._bulk_delete_costs(cost_ids)

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkCostType(self, payload: FinancialsMap) -> FinancialsMap: return self._apply_bulk_cost_type(payload)

    @Slot(str, "QVariantMap", result=str)
    def generateEntityCode(self, entity_type: str, payload: FinancialsMap) -> str: return self._generate_entity_code(entity_type, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def createCostItem(self, payload: FinancialsMap) -> FinancialsMap: return self._create_cost_item(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateCostItem(self, payload: FinancialsMap) -> FinancialsMap: return self._update_cost_item(payload)

    @Slot(str, result="QVariantMap")
    def deleteCostItem(self, cost_id: str) -> FinancialsMap: return self._delete_cost_item(cost_id)


__all__ = ["ProjectManagementFinancialsWorkspaceController"]
