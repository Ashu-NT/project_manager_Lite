from __future__ import annotations

from uuid import uuid4

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot
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
from src.ui_qml.modules.project_management.presenters.financials.destination_builder import (
    FINANCE_DESTINATIONS,
    FINANCE_SUBSECTIONS,
)

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
    activityChanged = Signal()
    actualSortKeyChanged = Signal()
    actualSortDirectionChanged = Signal()
    sourceAnalyticsChanged = Signal()
    costTypeAnalyticsChanged = Signal()
    notesChanged = Signal()
    forecastChanged = Signal()
    selectedForecastIdChanged = Signal()
    forecastVersionsChanged = Signal()
    forecastLinesChanged = Signal()
    selectedChangeIdChanged = Signal()
    financialChangesChanged = Signal()
    financialChangeImpactsChanged = Signal()
    commitmentSummaryChanged = Signal()
    commitmentsChanged = Signal()
    commitmentSortKeyChanged = Signal()
    commitmentSortDirectionChanged = Signal()
    baselineVarianceChanged = Signal()
    selectedBaselineIdChanged = Signal()
    baselineVersionsChanged = Signal()
    varianceBasisChanged = Signal()
    reportBasisChanged = Signal()
    financialProfileChanged = Signal()
    budgetVersionsChanged = Signal()
    budgetLinesChanged = Signal()
    selectedBudgetIdChanged = Signal()
    budgetVersionSortKeyChanged = Signal()
    budgetVersionSortDirectionChanged = Signal()
    budgetLineSortKeyChanged = Signal()
    budgetLineSortDirectionChanged = Signal()
    rateCardsChanged = Signal()
    rateLinesChanged = Signal()
    plannedCostVersionsChanged = Signal()
    plannedCostLinesChanged = Signal()
    billingProfileChanged = Signal()
    billingScheduleChanged = Signal()
    billingPreparationsChanged = Signal()
    commercialProjectionChanged = Signal()
    activeDestinationChanged = Signal()
    activeSubsectionChanged = Signal()

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
        self._activity = default_collection()
        self._actual_page = 1
        self._actual_sort_key = "metaText"
        self._actual_sort_direction = Qt.DescendingOrder.value
        self._source_analytics = default_collection()
        self._cost_type_analytics = default_collection()
        self._notes: list[str] = []
        self._forecast = default_forecast()
        self._selected_forecast_id = ""
        self._forecast_versions = default_collection()
        self._forecast_lines = default_collection()
        self._selected_change_id = ""
        self._financial_changes = default_collection()
        self._financial_change_impacts = default_collection()
        self._commitment_summary = default_commitment_summary()
        self._commitments = default_collection()
        self._commitment_page = 1
        self._commitment_sort_key = "metaText"
        self._commitment_sort_direction = Qt.DescendingOrder.value
        self._transaction_page_size = 50
        self._commitments_table_model = DynamicTableModel(self)
        self._baseline_variance: FinancialsObjectList = []
        self._selected_baseline_id = ""
        self._baseline_versions = default_collection()
        self._variance_basis = default_detail()
        self._report_basis = default_detail()
        self._financial_profile = default_detail()
        self._budget_versions = default_collection()
        self._budget_lines = default_collection()
        self._budget_versions_table_model = DynamicTableModel(self)
        self._budget_lines_table_model = DynamicTableModel(self)
        self._selected_budget_id = ""
        self._budget_version_page = 1
        self._budget_version_sort_key = "revision"
        self._budget_version_sort_direction = Qt.DescendingOrder.value
        self._budget_line_sort_key = "metaText"
        self._budget_line_sort_direction = Qt.DescendingOrder.value
        self._rate_cards = default_collection()
        self._rate_lines = default_collection()
        self._planned_cost_versions = default_collection()
        self._planned_cost_lines = default_collection()
        self._billing_profile = default_detail()
        self._billing_schedule = default_collection()
        self._billing_preparations = default_collection()
        self._commercial_projection = default_detail()
        self._budget_line_page = 1
        self._rate_line_page = 1
        self._planned_cost_line_page = 1
        self._billing_preparation_page = 1
        self._configuration_page_size = 50
        self._finance_destinations = FINANCE_DESTINATIONS
        self._finance_subsections = FINANCE_SUBSECTIONS
        self._active_destination = "overview"
        self._active_subsection = "summary"
        self._workspace_loaded = False
        self._shell_loaded = False
        self._refresh_generation = 0
        self._loaded_destination_keys: set[tuple[str, str, str]] = set()
        self._invalidated_destinations: set[str] = set(FINANCE_DESTINATIONS)
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

    @Property(str, notify=activeDestinationChanged)
    def activeDestination(self) -> str: return self._active_destination

    @Property(str, notify=activeSubsectionChanged)
    def activeSubsection(self) -> str: return self._active_subsection

    @Property("QVariantMap", notify=cashflowChanged)
    def cashflow(self) -> FinancialsMap: return self._cashflow

    @Property("QVariantMap", notify=ledgerChanged)
    def ledger(self) -> FinancialsMap: return self._ledger

    @Property("QVariantMap", notify=activityChanged)
    def activity(self) -> FinancialsMap: return self._activity

    @Property(QObject, constant=True)
    def ledgerTableModel(self) -> DynamicTableModel: return self._ledger_table_model

    @Property(str, notify=actualSortKeyChanged)
    def actualSortKey(self) -> str: return self._actual_sort_key

    @Property(int, notify=actualSortDirectionChanged)
    def actualSortDirection(self) -> int: return self._actual_sort_direction

    @Property("QVariantMap", notify=sourceAnalyticsChanged)
    def sourceAnalytics(self) -> FinancialsMap: return self._source_analytics

    @Property("QVariantMap", notify=costTypeAnalyticsChanged)
    def costTypeAnalytics(self) -> FinancialsMap: return self._cost_type_analytics

    @Property("QVariantList", notify=notesChanged)
    def notes(self) -> list[str]: return self._notes

    @Property("QVariantMap", notify=forecastChanged)
    def forecast(self) -> FinancialsMap: return self._forecast

    @Property(str, notify=selectedForecastIdChanged)
    def selectedForecastId(self) -> str: return self._selected_forecast_id

    @Property("QVariantMap", notify=forecastVersionsChanged)
    def forecastVersions(self) -> FinancialsMap: return self._forecast_versions

    @Property("QVariantMap", notify=forecastLinesChanged)
    def forecastLines(self) -> FinancialsMap: return self._forecast_lines

    @Property(str, notify=selectedChangeIdChanged)
    def selectedChangeId(self) -> str: return self._selected_change_id

    @Property("QVariantMap", notify=financialChangesChanged)
    def financialChanges(self) -> FinancialsMap: return self._financial_changes

    @Property("QVariantMap", notify=financialChangeImpactsChanged)
    def financialChangeImpacts(self) -> FinancialsMap: return self._financial_change_impacts

    @Property("QVariantMap", notify=commitmentSummaryChanged)
    def commitmentSummary(self) -> FinancialsMap: return self._commitment_summary

    @Property("QVariantMap", notify=commitmentsChanged)
    def commitments(self) -> FinancialsMap: return self._commitments

    @Property(QObject, constant=True)
    def commitmentsTableModel(self) -> DynamicTableModel: return self._commitments_table_model

    @Property(str, notify=commitmentSortKeyChanged)
    def commitmentSortKey(self) -> str: return self._commitment_sort_key

    @Property(int, notify=commitmentSortDirectionChanged)
    def commitmentSortDirection(self) -> int: return self._commitment_sort_direction

    @Property("QVariantList", notify=baselineVarianceChanged)
    def baselineVariance(self) -> FinancialsObjectList: return self._baseline_variance

    @Property(str, notify=selectedBaselineIdChanged)
    def selectedBaselineId(self) -> str: return self._selected_baseline_id

    @Property("QVariantMap", notify=baselineVersionsChanged)
    def baselineVersions(self) -> FinancialsMap: return self._baseline_versions

    @Property("QVariantMap", notify=varianceBasisChanged)
    def varianceBasis(self) -> FinancialsMap: return self._variance_basis

    @Property("QVariantMap", notify=reportBasisChanged)
    def reportBasis(self) -> FinancialsMap: return self._report_basis

    @Property("QVariantMap", notify=financialProfileChanged)
    def financialProfile(self) -> FinancialsMap: return self._financial_profile

    @Property("QVariantMap", notify=budgetVersionsChanged)
    def budgetVersions(self) -> FinancialsMap: return self._budget_versions

    @Property("QVariantMap", notify=budgetLinesChanged)
    def budgetLines(self) -> FinancialsMap: return self._budget_lines

    @Property(QObject, constant=True)
    def budgetVersionsTableModel(self) -> DynamicTableModel:
        return self._budget_versions_table_model

    @Property(QObject, constant=True)
    def budgetLinesTableModel(self) -> DynamicTableModel:
        return self._budget_lines_table_model

    @Property(str, notify=selectedBudgetIdChanged)
    def selectedBudgetId(self) -> str: return self._selected_budget_id

    @Property(str, notify=budgetVersionSortKeyChanged)
    def budgetVersionSortKey(self) -> str: return self._budget_version_sort_key

    @Property(int, notify=budgetVersionSortDirectionChanged)
    def budgetVersionSortDirection(self) -> int:
        return self._budget_version_sort_direction

    @Property(str, notify=budgetLineSortKeyChanged)
    def budgetLineSortKey(self) -> str: return self._budget_line_sort_key

    @Property(int, notify=budgetLineSortDirectionChanged)
    def budgetLineSortDirection(self) -> int: return self._budget_line_sort_direction

    @Property("QVariantMap", notify=rateCardsChanged)
    def rateCards(self) -> FinancialsMap: return self._rate_cards

    @Property("QVariantMap", notify=rateLinesChanged)
    def rateLines(self) -> FinancialsMap: return self._rate_lines

    @Property("QVariantMap", notify=plannedCostVersionsChanged)
    def plannedCostVersions(self) -> FinancialsMap: return self._planned_cost_versions

    @Property("QVariantMap", notify=plannedCostLinesChanged)
    def plannedCostLines(self) -> FinancialsMap: return self._planned_cost_lines

    @Property("QVariantMap", notify=billingProfileChanged)
    def billingProfile(self) -> FinancialsMap: return self._billing_profile

    @Property("QVariantMap", notify=billingScheduleChanged)
    def billingSchedule(self) -> FinancialsMap: return self._billing_schedule

    @Property("QVariantMap", notify=billingPreparationsChanged)
    def billingPreparations(self) -> FinancialsMap: return self._billing_preparations

    @Property("QVariantMap", notify=commercialProjectionChanged)
    def commercialProjection(self) -> FinancialsMap: return self._commercial_projection

    @Slot()
    def refresh(self) -> None: self._refresh()

    @Slot(str)
    def selectProject(self, project_id: str) -> None: self._select_project(project_id)

    @Slot(str)
    def selectFinanceDestination(self, destination: str) -> None:
        self._select_destination(destination)

    @Slot(str)
    def selectFinanceSubsection(self, subsection: str) -> None:
        self._select_subsection(subsection)

    @Slot(str, str)
    def exportFinancials(self, report_format: str, output_path: str) -> None:
        self._export_financials(report_format, output_path)

    @Slot(str)
    def selectForecastVersion(self, forecast_id: str) -> None:
        self._select_forecast_version(forecast_id)

    @Slot(str)
    def selectBudgetVersion(self, budget_id: str) -> None:
        self._select_budget_version(budget_id)

    @Slot(str)
    def selectFinancialChange(self, change_id: str) -> None:
        self._select_financial_change(change_id)

    @Slot(str)
    def selectVarianceBaseline(self, baseline_id: str) -> None:
        self._select_variance_baseline(baseline_id)

    @Slot("QVariantMap", result="QVariantMap")
    def createManualActual(self, payload: FinancialsMap) -> FinancialsMap: return self._create_manual_actual(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def submitActual(self, payload: FinancialsMap) -> FinancialsMap: return self._submit_actual(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def approveActual(self, payload: FinancialsMap) -> FinancialsMap: return self._approve_actual(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def rejectActual(self, payload: FinancialsMap) -> FinancialsMap: return self._reject_actual(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def postActual(self, payload: FinancialsMap) -> FinancialsMap: return self._post_actual(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def reverseActual(self, payload: FinancialsMap) -> FinancialsMap: return self._reverse_actual(payload)

    @Slot(result=str)
    def newFinancialCommandId(self) -> str: return str(uuid4())

    @Slot(str, int)
    def setConfigurationPage(self, collection: str, page: int) -> None:
        self._set_configuration_page(collection, page)

    @Slot(int)
    def setBudgetVersionPage(self, page: int) -> None:
        self._set_budget_version_page(page)

    @Slot(str, int)
    def setBudgetVersionSort(self, sort_key: str, sort_direction: int) -> None:
        self._set_budget_version_sort(sort_key, sort_direction)

    @Slot(str, int)
    def setBudgetLineSort(self, sort_key: str, sort_direction: int) -> None:
        self._set_budget_line_sort(sort_key, sort_direction)

    @Slot(int)
    def setActualPage(self, page: int) -> None: self._set_actual_page(page)

    @Slot(int)
    def setActualPageSize(self, page_size: int) -> None:
        self._set_transaction_page_size(page_size)

    @Slot(str, int)
    def setActualSort(self, sort_key: str, sort_direction: int) -> None:
        self._set_actual_sort(sort_key, sort_direction)

    @Slot(int)
    def setCommitmentPage(self, page: int) -> None: self._set_commitment_page(page)

    @Slot(int)
    def setCommitmentPageSize(self, page_size: int) -> None:
        self._set_transaction_page_size(page_size)

    @Slot(str, int)
    def setCommitmentSort(self, sort_key: str, sort_direction: int) -> None:
        self._set_commitment_sort(sort_key, sort_direction)


__all__ = ["ProjectManagementFinancialsWorkspaceController"]
