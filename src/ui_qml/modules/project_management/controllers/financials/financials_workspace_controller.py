from __future__ import annotations

from uuid import uuid4

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
)
from src.ui_qml.modules.project_management.controllers.financials.financials_mutation_mixin import FinancialsMutationMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_refresh_mixin import FinancialsRefreshMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_selection_mixin import FinancialsSelectionMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_state_mixin import FinancialsStateMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_types import (
    FinancialsMap,
    FinancialsObjectList,
    default_collection,
    default_commitment_summary,
    default_forecast,
    default_overview,
    default_detail,
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
    FinancialsMutationMixin,
    FinancialsStateMixin,
):
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    taskOptionsChanged = Signal()
    manualActualOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    cashflowChanged = Signal()
    ledgerChanged = Signal()
    sourceAnalyticsChanged = Signal()
    costTypeAnalyticsChanged = Signal()
    notesChanged = Signal()
    forecastChanged = Signal()
    commitmentSummaryChanged = Signal()
    baselineVarianceChanged = Signal()
    financialProfileChanged = Signal()
    budgetVersionsChanged = Signal()
    budgetLinesChanged = Signal()
    rateCardsChanged = Signal()
    rateLinesChanged = Signal()
    plannedCostVersionsChanged = Signal()
    plannedCostLinesChanged = Signal()

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
        self._task_options: FinancialsObjectList = []
        self._manual_actual_options: FinancialsMap = {
            "currencyCode": "",
            "costCodes": [],
            "entryKinds": [],
        }
        self._selected_project_id = ""
        self._ledger_table_model = DynamicTableModel(self)
        self._cashflow = default_collection()
        self._ledger = default_collection()
        self._source_analytics = default_collection()
        self._cost_type_analytics = default_collection()
        self._notes: list[str] = []
        self._forecast = default_forecast()
        self._commitment_summary = default_commitment_summary()
        self._baseline_variance: FinancialsObjectList = []
        self._financial_profile = default_detail()
        self._budget_versions = default_collection()
        self._budget_lines = default_collection()
        self._rate_cards = default_collection()
        self._rate_lines = default_collection()
        self._planned_cost_versions = default_collection()
        self._planned_cost_lines = default_collection()
        self._budget_line_page = 1
        self._rate_line_page = 1
        self._planned_cost_line_page = 1
        self._configuration_page_size = 50
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> FinancialsMap: return self._overview

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> FinancialsObjectList: return self._project_options

    @Property("QVariantList", notify=taskOptionsChanged)
    def taskOptions(self) -> FinancialsObjectList: return self._task_options

    @Property("QVariantMap", notify=manualActualOptionsChanged)
    def manualActualOptions(self) -> FinancialsMap: return self._manual_actual_options

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str: return self._selected_project_id

    @Property("QVariantMap", notify=cashflowChanged)
    def cashflow(self) -> FinancialsMap: return self._cashflow

    @Property("QVariantMap", notify=ledgerChanged)
    def ledger(self) -> FinancialsMap: return self._ledger

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

    @Property("QVariantMap", notify=financialProfileChanged)
    def financialProfile(self) -> FinancialsMap: return self._financial_profile

    @Property("QVariantMap", notify=budgetVersionsChanged)
    def budgetVersions(self) -> FinancialsMap: return self._budget_versions

    @Property("QVariantMap", notify=budgetLinesChanged)
    def budgetLines(self) -> FinancialsMap: return self._budget_lines

    @Property("QVariantMap", notify=rateCardsChanged)
    def rateCards(self) -> FinancialsMap: return self._rate_cards

    @Property("QVariantMap", notify=rateLinesChanged)
    def rateLines(self) -> FinancialsMap: return self._rate_lines

    @Property("QVariantMap", notify=plannedCostVersionsChanged)
    def plannedCostVersions(self) -> FinancialsMap: return self._planned_cost_versions

    @Property("QVariantMap", notify=plannedCostLinesChanged)
    def plannedCostLines(self) -> FinancialsMap: return self._planned_cost_lines

    @Slot()
    def refresh(self) -> None: self._refresh()

    @Slot(str)
    def selectProject(self, project_id: str) -> None: self._select_project(project_id)

    @Slot(str, result="QVariantMap")
    def computeForecast(self, method: str) -> FinancialsMap: return self._compute_forecast(method)

    @Slot()
    def exportFinancials(self) -> None: self._export_financials()

    @Slot("QVariantMap", result="QVariantMap")
    def createManualActual(self, payload: FinancialsMap) -> FinancialsMap: return self._create_manual_actual(payload)

    @Slot(result=str)
    def newFinancialCommandId(self) -> str: return str(uuid4())

    @Slot(str, int)
    def setConfigurationPage(self, collection: str, page: int) -> None:
        self._set_configuration_page(collection, page)


__all__ = ["ProjectManagementFinancialsWorkspaceController"]
