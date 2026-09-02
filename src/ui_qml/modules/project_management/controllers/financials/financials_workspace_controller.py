from __future__ import annotations

import calendar
from datetime import date
from uuid import uuid4

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
)
from src.ui_qml.modules.project_management.controllers.financials.financials_mutation_mixin import FinancialsMutationMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_lookup_mixin import FinancialsLookupMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_refresh_mixin import FinancialsRefreshMixin
from src.ui_qml.modules.project_management.controllers.financials.forecast_domain_event_binder import (
    on_forecast_approved_basis_stale,
    on_forecast_planning_stale,
)
from src.ui_qml.modules.project_management.controllers.financials.financial_setup_domain_event_binder import (
    on_financial_profile_stale,
)
from src.ui_qml.modules.project_management.controllers.financials.rate_card_domain_event_binder import (
    on_rate_card_detail_stale,
    on_rate_card_list_stale,
    on_rate_card_list_stale_for_project,
)
from src.ui_qml.modules.project_management.controllers.financials.financials_selection_mixin import FinancialsSelectionMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_state_mixin import FinancialsStateMixin
from src.ui_qml.modules.project_management.controllers.financials.financials_types import (
    FinancialsMap,
    FinancialsObjectList,
    default_collection,
    default_commitment_summary,
    default_overview,
    default_detail,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectFinancialsWorkspacePresenter,
    ProjectManagementWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.shared.models.currency_options import (
    CURRENCY_OPTIONS,
    DEFAULT_CURRENCY_CODE,
)
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
    FinancialsLookupMixin,
    FinancialsStateMixin,
):
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    manualActualDefaultsChanged = Signal()
    selectedProjectIdChanged = Signal()
    costPhasingChanged = Signal()
    costPhasingBasisChanged = Signal()
    evmBasisChanged = Signal()
    evmMetricsChanged = Signal()
    varianceMetricsChanged = Signal()
    reportDefinitionsChanged = Signal()
    performanceQueryStateChanged = Signal()
    ledgerChanged = Signal()
    activityChanged = Signal()
    actualSortKeyChanged = Signal()
    actualSortDirectionChanged = Signal()
    selectedForecastIdChanged = Signal()
    forecastVersionsChanged = Signal()
    forecastLinesChanged = Signal()
    selectedForecastChanged = Signal()
    forecastVersionSortKeyChanged = Signal()
    forecastVersionSortDirectionChanged = Signal()
    forecastLineSortKeyChanged = Signal()
    forecastLineSortDirectionChanged = Signal()
    forecastFiltersChanged = Signal()
    selectedChangeIdChanged = Signal()
    selectedChangeChanged = Signal()
    financialChangesChanged = Signal()
    financialChangeImpactsChanged = Signal()
    changeSortKeyChanged = Signal()
    changeSortDirectionChanged = Signal()
    impactSortKeyChanged = Signal()
    impactSortDirectionChanged = Signal()
    changeFiltersChanged = Signal()
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
    showCreateBudgetVersionChanged = Signal()
    canCreateBudgetVersionChanged = Signal()
    createBudgetVersionDisabledReasonChanged = Signal()
    budgetVersionSortKeyChanged = Signal()
    budgetVersionSortDirectionChanged = Signal()
    budgetLineSortKeyChanged = Signal()
    budgetLineSortDirectionChanged = Signal()
    rateCardsChanged = Signal()
    rateLinesChanged = Signal()
    selectedRateCardIdChanged = Signal()
    selectedRateCardChanged = Signal()
    rateCardSortKeyChanged = Signal()
    rateCardSortDirectionChanged = Signal()
    rateLineSortKeyChanged = Signal()
    rateLineSortDirectionChanged = Signal()
    rateFiltersChanged = Signal()
    plannedCostVersionsChanged = Signal()
    plannedCostLinesChanged = Signal()
    selectedPlannedCostVersionIdChanged = Signal()
    plannedCostVersionSortKeyChanged = Signal()
    plannedCostVersionSortDirectionChanged = Signal()
    plannedCostLineSortKeyChanged = Signal()
    plannedCostLineSortDirectionChanged = Signal()
    billingProfileChanged = Signal()
    billingScheduleChanged = Signal()
    billingPreparationsChanged = Signal()
    billingPreparationLinesChanged = Signal()
    selectedBillingPreparationChanged = Signal()
    selectedBillingPreparationIdChanged = Signal()
    billingQueryStateChanged = Signal()
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
        self._manual_actual_defaults: FinancialsMap = {
            "currencyCode": "",
            "entryKinds": [],
        }
        self._selected_project_id = ""
        self._active_tenant_id = ""
        self._active_organization_id = ""
        self._ledger_table_model = DynamicTableModel(self)
        self._cost_phasing = default_collection()
        self._cost_phasing_basis = default_detail()
        self._evm_basis = default_detail()
        self._evm_metrics = default_collection()
        self._variance_metrics = default_collection()
        self._report_definitions = default_collection()
        today = date.today()
        self._performance_as_of_date = today
        self._cost_phasing_date_from = date(today.year - 1, today.month, 1)
        self._cost_phasing_date_to = today
        self._cost_phasing_granularity = "month"
        self._ledger = default_collection()
        self._activity = default_collection()
        self._actual_page = 1
        self._actual_sort_key = "metaText"
        self._actual_sort_direction = Qt.DescendingOrder.value
        self._selected_forecast_id = ""
        self._selected_forecast = default_detail()
        self._forecast_versions = default_collection()
        self._forecast_lines = default_collection()
        self._forecast_versions_table_model = DynamicTableModel(self)
        self._forecast_lines_table_model = DynamicTableModel(self)
        self._forecast_version_page = 1
        self._forecast_line_page = 1
        self._forecast_version_sort_key = "revision"
        self._forecast_version_sort_direction = Qt.DescendingOrder.value
        self._forecast_line_sort_key = "title"
        self._forecast_line_sort_direction = Qt.AscendingOrder.value
        self._forecast_version_search = ""
        self._forecast_version_status = ""
        self._forecast_generation_mode = ""
        self._forecast_line_search = ""
        self._forecast_line_source_type = ""
        self._selected_change_id = ""
        self._selected_change = default_detail()
        self._financial_changes = default_collection()
        self._financial_change_impacts = default_collection()
        self._financial_changes_table_model = DynamicTableModel(self)
        self._financial_change_impacts_table_model = DynamicTableModel(self)
        self._change_page = 1
        self._impact_page = 1
        self._change_sort_key = "metaText"
        self._change_sort_direction = Qt.DescendingOrder.value
        self._impact_sort_key = "metaText"
        self._impact_sort_direction = Qt.AscendingOrder.value
        self._change_search = ""
        self._change_status = ""
        self._change_approval_status = ""
        self._change_applied_state = ""
        self._impact_search = ""
        self._impact_type = ""
        self._impact_applied_state = ""
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
        self._show_create_budget_version = False
        self._can_create_budget_version = False
        self._create_budget_version_disabled_reason = ""
        self._budget_version_page = 1
        self._budget_version_sort_key = "revision"
        self._budget_version_sort_direction = Qt.DescendingOrder.value
        self._budget_line_sort_key = "metaText"
        self._budget_line_sort_direction = Qt.DescendingOrder.value
        self._rate_cards = default_collection()
        self._rate_lines = default_collection()
        self._selected_rate_card_id = ""
        self._selected_rate_card = default_detail()
        self._rate_cards_table_model = DynamicTableModel(self)
        self._rate_lines_table_model = DynamicTableModel(self)
        self._rate_card_page = 1
        self._rate_card_sort_key = "title"
        self._rate_card_sort_direction = Qt.AscendingOrder.value
        self._rate_line_sort_key = "title"
        self._rate_line_sort_direction = Qt.AscendingOrder.value
        self._rate_card_search = ""
        self._rate_card_scope = ""
        self._rate_card_status = ""
        self._rate_line_search = ""
        self._rate_line_rate_type = ""
        self._rate_line_status = ""
        self._rate_line_effective_status = ""
        self._planned_cost_versions = default_collection()
        self._planned_cost_lines = default_collection()
        self._planned_cost_versions_table_model = DynamicTableModel(self)
        self._planned_cost_lines_table_model = DynamicTableModel(self)
        self._selected_planned_cost_version_id = ""
        self._planned_cost_version_page = 1
        self._planned_cost_version_sort_key = "revision"
        self._planned_cost_version_sort_direction = Qt.DescendingOrder.value
        self._planned_cost_line_sort_key = "title"
        self._planned_cost_line_sort_direction = Qt.AscendingOrder.value
        self._billing_profile = default_detail()
        self._billing_schedule = default_collection()
        self._billing_preparations = default_collection()
        self._billing_preparation_lines = default_collection()
        self._selected_billing_preparation_id = ""
        self._selected_billing_preparation = default_detail()
        self._billing_schedule_table_model = DynamicTableModel(self)
        self._billing_preparations_table_model = DynamicTableModel(self)
        self._billing_preparation_lines_table_model = DynamicTableModel(self)
        self._billing_schedule_page = 1
        self._billing_line_page = 1
        self._billing_schedule_sort_key = "supportingText"
        self._billing_schedule_sort_direction = Qt.AscendingOrder.value
        self._billing_preparation_sort_key = "metaText"
        self._billing_preparation_sort_direction = Qt.DescendingOrder.value
        self._billing_line_sort_key = "metaText"
        self._billing_line_sort_direction = Qt.AscendingOrder.value
        self._billing_schedule_search = ""
        self._billing_schedule_status = ""
        self._billing_schedule_source_state = ""
        self._billing_preparation_search = ""
        self._billing_preparation_status = ""
        self._billing_preparation_method = ""
        self._billing_preparation_approval_status = ""
        self._billing_preparation_delivery_state = ""
        self._billing_preparation_correction_state = ""
        self._billing_line_search = ""
        self._billing_line_source_type = ""
        self._billing_line_source_state = ""
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

    @Property("QVariantMap", notify=manualActualDefaultsChanged)
    def manualActualDefaults(self) -> FinancialsMap: return self._manual_actual_defaults

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str: return self._selected_project_id

    @Property(str, notify=activeDestinationChanged)
    def activeDestination(self) -> str: return self._active_destination

    @Property(str, notify=activeSubsectionChanged)
    def activeSubsection(self) -> str: return self._active_subsection

    @Property("QVariantMap", notify=costPhasingChanged)
    def costPhasing(self) -> FinancialsMap: return self._cost_phasing

    @Property("QVariantMap", notify=costPhasingBasisChanged)
    def costPhasingBasis(self) -> FinancialsMap: return self._cost_phasing_basis

    @Property("QVariantMap", notify=evmBasisChanged)
    def evmBasis(self) -> FinancialsMap: return self._evm_basis

    @Property("QVariantMap", notify=evmMetricsChanged)
    def evmMetrics(self) -> FinancialsMap: return self._evm_metrics

    @Property("QVariantMap", notify=varianceMetricsChanged)
    def varianceMetrics(self) -> FinancialsMap: return self._variance_metrics

    @Property("QVariantMap", notify=reportDefinitionsChanged)
    def reportDefinitions(self) -> FinancialsMap: return self._report_definitions

    @Property(str, notify=performanceQueryStateChanged)
    def performanceAsOfDate(self) -> str: return self._performance_as_of_date.isoformat()

    @Property(str, notify=performanceQueryStateChanged)
    def costPhasingDateFrom(self) -> str: return self._cost_phasing_date_from.isoformat()

    @Property(str, notify=performanceQueryStateChanged)
    def costPhasingDateTo(self) -> str: return self._cost_phasing_date_to.isoformat()

    @Property(str, notify=performanceQueryStateChanged)
    def costPhasingGranularity(self) -> str: return self._cost_phasing_granularity

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

    @Property(str, notify=selectedForecastIdChanged)
    def selectedForecastId(self) -> str: return self._selected_forecast_id

    @Property("QVariantMap", notify=forecastVersionsChanged)
    def forecastVersions(self) -> FinancialsMap: return self._forecast_versions

    @Property("QVariantMap", notify=forecastLinesChanged)
    def forecastLines(self) -> FinancialsMap: return self._forecast_lines

    @Property("QVariantMap", notify=selectedForecastChanged)
    def selectedForecast(self) -> FinancialsMap: return self._selected_forecast

    @Property(QObject, constant=True)
    def forecastVersionsTableModel(self) -> DynamicTableModel:
        return self._forecast_versions_table_model

    @Property(QObject, constant=True)
    def forecastLinesTableModel(self) -> DynamicTableModel:
        return self._forecast_lines_table_model

    @Property(str, notify=forecastVersionSortKeyChanged)
    def forecastVersionSortKey(self) -> str: return self._forecast_version_sort_key

    @Property(int, notify=forecastVersionSortDirectionChanged)
    def forecastVersionSortDirection(self) -> int:
        return self._forecast_version_sort_direction

    @Property(str, notify=forecastLineSortKeyChanged)
    def forecastLineSortKey(self) -> str: return self._forecast_line_sort_key

    @Property(int, notify=forecastLineSortDirectionChanged)
    def forecastLineSortDirection(self) -> int:
        return self._forecast_line_sort_direction

    @Property(str, notify=forecastFiltersChanged)
    def forecastVersionSearch(self) -> str: return self._forecast_version_search

    @Property(str, notify=forecastFiltersChanged)
    def forecastVersionStatus(self) -> str: return self._forecast_version_status

    @Property(str, notify=forecastFiltersChanged)
    def forecastGenerationMode(self) -> str: return self._forecast_generation_mode

    @Property(str, notify=forecastFiltersChanged)
    def forecastLineSearch(self) -> str: return self._forecast_line_search

    @Property(str, notify=forecastFiltersChanged)
    def forecastLineSourceType(self) -> str: return self._forecast_line_source_type

    @Property(str, notify=selectedChangeIdChanged)
    def selectedChangeId(self) -> str: return self._selected_change_id

    @Property("QVariantMap", notify=selectedChangeChanged)
    def selectedChange(self) -> FinancialsMap: return self._selected_change

    @Property("QVariantMap", notify=financialChangesChanged)
    def financialChanges(self) -> FinancialsMap: return self._financial_changes

    @Property("QVariantMap", notify=financialChangeImpactsChanged)
    def financialChangeImpacts(self) -> FinancialsMap: return self._financial_change_impacts

    @Property(QObject, constant=True)
    def financialChangesTableModel(self) -> DynamicTableModel:
        return self._financial_changes_table_model

    @Property(QObject, constant=True)
    def financialChangeImpactsTableModel(self) -> DynamicTableModel:
        return self._financial_change_impacts_table_model

    @Property(str, notify=changeSortKeyChanged)
    def changeSortKey(self) -> str: return self._change_sort_key

    @Property(int, notify=changeSortDirectionChanged)
    def changeSortDirection(self) -> int: return self._change_sort_direction

    @Property(str, notify=impactSortKeyChanged)
    def impactSortKey(self) -> str: return self._impact_sort_key

    @Property(int, notify=impactSortDirectionChanged)
    def impactSortDirection(self) -> int: return self._impact_sort_direction

    @Property(str, notify=changeFiltersChanged)
    def changeSearch(self) -> str: return self._change_search

    @Property(str, notify=changeFiltersChanged)
    def changeStatus(self) -> str: return self._change_status

    @Property(str, notify=changeFiltersChanged)
    def changeApprovalStatus(self) -> str: return self._change_approval_status

    @Property(str, notify=changeFiltersChanged)
    def changeAppliedState(self) -> str: return self._change_applied_state

    @Property(str, notify=changeFiltersChanged)
    def impactSearch(self) -> str: return self._impact_search

    @Property(str, notify=changeFiltersChanged)
    def impactType(self) -> str: return self._impact_type

    @Property(str, notify=changeFiltersChanged)
    def impactAppliedState(self) -> str: return self._impact_applied_state

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

    @Property(bool, notify=showCreateBudgetVersionChanged)
    def showCreateBudgetVersion(self) -> bool: return self._show_create_budget_version

    @Property(bool, notify=canCreateBudgetVersionChanged)
    def canCreateBudgetVersion(self) -> bool: return self._can_create_budget_version

    @Property(str, notify=createBudgetVersionDisabledReasonChanged)
    def createBudgetVersionDisabledReason(self) -> str:
        return self._create_budget_version_disabled_reason

    @Property("QVariantList", constant=True)
    def currencyOptions(self) -> list[dict[str, str]]: return CURRENCY_OPTIONS

    @Property(str, constant=True)
    def defaultCurrencyCode(self) -> str: return DEFAULT_CURRENCY_CODE

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

    @Property(str, notify=selectedRateCardIdChanged)
    def selectedRateCardId(self) -> str: return self._selected_rate_card_id

    @Property("QVariantMap", notify=selectedRateCardChanged)
    def selectedRateCard(self) -> FinancialsMap: return self._selected_rate_card

    @Property(QObject, constant=True)
    def rateCardsTableModel(self) -> DynamicTableModel: return self._rate_cards_table_model

    @Property(QObject, constant=True)
    def rateLinesTableModel(self) -> DynamicTableModel: return self._rate_lines_table_model

    @Property(str, notify=rateCardSortKeyChanged)
    def rateCardSortKey(self) -> str: return self._rate_card_sort_key

    @Property(int, notify=rateCardSortDirectionChanged)
    def rateCardSortDirection(self) -> int: return self._rate_card_sort_direction

    @Property(str, notify=rateLineSortKeyChanged)
    def rateLineSortKey(self) -> str: return self._rate_line_sort_key

    @Property(int, notify=rateLineSortDirectionChanged)
    def rateLineSortDirection(self) -> int: return self._rate_line_sort_direction

    @Property(str, notify=rateFiltersChanged)
    def rateCardSearch(self) -> str: return self._rate_card_search

    @Property(str, notify=rateFiltersChanged)
    def rateCardScope(self) -> str: return self._rate_card_scope

    @Property(str, notify=rateFiltersChanged)
    def rateCardStatus(self) -> str: return self._rate_card_status

    @Property(str, notify=rateFiltersChanged)
    def rateLineSearch(self) -> str: return self._rate_line_search

    @Property(str, notify=rateFiltersChanged)
    def rateLineRateType(self) -> str: return self._rate_line_rate_type

    @Property(str, notify=rateFiltersChanged)
    def rateLineStatus(self) -> str: return self._rate_line_status

    @Property(str, notify=rateFiltersChanged)
    def rateLineEffectiveStatus(self) -> str: return self._rate_line_effective_status

    @Property("QVariantMap", notify=plannedCostVersionsChanged)
    def plannedCostVersions(self) -> FinancialsMap: return self._planned_cost_versions

    @Property("QVariantMap", notify=plannedCostLinesChanged)
    def plannedCostLines(self) -> FinancialsMap: return self._planned_cost_lines

    @Property(QObject, constant=True)
    def plannedCostVersionsTableModel(self) -> DynamicTableModel:
        return self._planned_cost_versions_table_model

    @Property(QObject, constant=True)
    def plannedCostLinesTableModel(self) -> DynamicTableModel:
        return self._planned_cost_lines_table_model

    @Property(str, notify=selectedPlannedCostVersionIdChanged)
    def selectedPlannedCostVersionId(self) -> str:
        return self._selected_planned_cost_version_id

    @Property(str, notify=plannedCostVersionSortKeyChanged)
    def plannedCostVersionSortKey(self) -> str:
        return self._planned_cost_version_sort_key

    @Property(int, notify=plannedCostVersionSortDirectionChanged)
    def plannedCostVersionSortDirection(self) -> int:
        return self._planned_cost_version_sort_direction

    @Property(str, notify=plannedCostLineSortKeyChanged)
    def plannedCostLineSortKey(self) -> str:
        return self._planned_cost_line_sort_key

    @Property(int, notify=plannedCostLineSortDirectionChanged)
    def plannedCostLineSortDirection(self) -> int:
        return self._planned_cost_line_sort_direction

    @Property("QVariantMap", notify=billingProfileChanged)
    def billingProfile(self) -> FinancialsMap: return self._billing_profile

    @Property("QVariantMap", notify=billingScheduleChanged)
    def billingSchedule(self) -> FinancialsMap: return self._billing_schedule

    @Property("QVariantMap", notify=billingPreparationsChanged)
    def billingPreparations(self) -> FinancialsMap: return self._billing_preparations

    @Property("QVariantMap", notify=billingPreparationLinesChanged)
    def billingPreparationLines(self) -> FinancialsMap: return self._billing_preparation_lines

    @Property("QVariantMap", notify=selectedBillingPreparationChanged)
    def selectedBillingPreparation(self) -> FinancialsMap: return self._selected_billing_preparation

    @Property(str, notify=selectedBillingPreparationIdChanged)
    def selectedBillingPreparationId(self) -> str: return self._selected_billing_preparation_id

    @Property(QObject, constant=True)
    def billingScheduleTableModel(self) -> DynamicTableModel: return self._billing_schedule_table_model

    @Property(QObject, constant=True)
    def billingPreparationsTableModel(self) -> DynamicTableModel: return self._billing_preparations_table_model

    @Property(QObject, constant=True)
    def billingPreparationLinesTableModel(self) -> DynamicTableModel: return self._billing_preparation_lines_table_model

    @Property(str, notify=billingQueryStateChanged)
    def billingScheduleSortKey(self) -> str: return self._billing_schedule_sort_key

    @Property(int, notify=billingQueryStateChanged)
    def billingScheduleSortDirection(self) -> int: return self._billing_schedule_sort_direction

    @Property(str, notify=billingQueryStateChanged)
    def billingPreparationSortKey(self) -> str: return self._billing_preparation_sort_key

    @Property(int, notify=billingQueryStateChanged)
    def billingPreparationSortDirection(self) -> int: return self._billing_preparation_sort_direction

    @Property(str, notify=billingQueryStateChanged)
    def billingLineSortKey(self) -> str: return self._billing_line_sort_key

    @Property(int, notify=billingQueryStateChanged)
    def billingLineSortDirection(self) -> int: return self._billing_line_sort_direction

    @Property(str, notify=billingQueryStateChanged)
    def billingScheduleSearch(self) -> str: return self._billing_schedule_search

    @Property(str, notify=billingQueryStateChanged)
    def billingScheduleStatus(self) -> str: return self._billing_schedule_status

    @Property(str, notify=billingQueryStateChanged)
    def billingScheduleSourceState(self) -> str: return self._billing_schedule_source_state

    @Property(str, notify=billingQueryStateChanged)
    def billingPreparationSearch(self) -> str: return self._billing_preparation_search

    @Property(str, notify=billingQueryStateChanged)
    def billingPreparationStatus(self) -> str: return self._billing_preparation_status

    @Property(str, notify=billingQueryStateChanged)
    def billingPreparationMethod(self) -> str: return self._billing_preparation_method

    @Property(str, notify=billingQueryStateChanged)
    def billingPreparationApprovalStatus(self) -> str: return self._billing_preparation_approval_status

    @Property(str, notify=billingQueryStateChanged)
    def billingPreparationDeliveryState(self) -> str: return self._billing_preparation_delivery_state

    @Property(str, notify=billingQueryStateChanged)
    def billingPreparationCorrectionState(self) -> str: return self._billing_preparation_correction_state

    @Property(str, notify=billingQueryStateChanged)
    def billingLineSearch(self) -> str: return self._billing_line_search

    @Property(str, notify=billingQueryStateChanged)
    def billingLineSourceType(self) -> str: return self._billing_line_source_type

    @Property(str, notify=billingQueryStateChanged)
    def billingLineSourceState(self) -> str: return self._billing_line_source_state

    @Property("QVariantMap", notify=commercialProjectionChanged)
    def commercialProjection(self) -> FinancialsMap: return self._commercial_projection

    @Slot()
    def refresh(self) -> None: self._refresh()

    def onForecastPlanningStale(self, project_id: str) -> None:
        on_forecast_planning_stale(self, project_id)

    def onForecastApprovedBasisStale(self, project_id: str) -> None:
        on_forecast_approved_basis_stale(self, project_id)

    def onFinancialProfileStale(self, project_id: str) -> None:
        on_financial_profile_stale(self, project_id)

    def onRateCardListStale(self, rate_card_id: str) -> None:
        on_rate_card_list_stale(self, rate_card_id)

    def onRateCardListStaleForProject(self, project_id: str) -> None:
        on_rate_card_list_stale_for_project(self, project_id)

    def onRateCardDetailStale(self, rate_card_id: str) -> None:
        on_rate_card_detail_stale(self, rate_card_id)

    @Slot(str)
    def selectProject(self, project_id: str) -> None: self._select_project(project_id)

    @Slot(str)
    def selectFinanceDestination(self, destination: str) -> None:
        self._select_destination(destination)

    @Slot(str)
    def selectFinanceSubsection(self, subsection: str) -> None:
        self._select_subsection(subsection)

    @Slot(int, str)
    def setCostPhasingPreset(self, months: int, granularity: str) -> None:
        requested_months = int(months)
        if requested_months <= 0:
            requested_months = max(
                1,
                (self._cost_phasing_date_to.year - self._cost_phasing_date_from.year) * 12
                + self._cost_phasing_date_to.month
                - self._cost_phasing_date_from.month,
            )
        bounded_months = min(requested_months, 36)
        normalized_granularity = str(granularity or "").strip().lower()
        if normalized_granularity not in {"month", "quarter"}:
            self._set_error_message("Cost Phasing granularity must be month or quarter.")
            return
        range_to = self._performance_as_of_date
        index = range_to.year * 12 + range_to.month - bounded_months
        year, month_index = divmod(index, 12)
        month = month_index + 1
        range_from = date(
            year,
            month,
            min(range_to.day, calendar.monthrange(year, month)[1]),
        )
        changed = (
            range_from != self._cost_phasing_date_from
            or range_to != self._cost_phasing_date_to
            or normalized_granularity != self._cost_phasing_granularity
        )
        if not changed:
            return
        self._cost_phasing_date_from = range_from
        self._cost_phasing_date_to = range_to
        self._cost_phasing_granularity = normalized_granularity
        self.performanceQueryStateChanged.emit()
        if self._active_destination == "performance" and self._active_subsection == "cost_phasing":
            self.refresh()

    @Slot(str, str)
    def exportFinancials(self, report_format: str, output_path: str) -> None:
        self._export_financials(report_format, output_path)

    @Slot(str)
    def selectForecastVersion(self, forecast_id: str) -> None:
        self._select_forecast_version(forecast_id)

    @Slot(int)
    def setForecastVersionPage(self, page: int) -> None:
        self._set_forecast_version_page(page)

    @Slot(int)
    def setForecastLinePage(self, page: int) -> None:
        self._set_forecast_line_page(page)

    @Slot(str, int)
    def setForecastVersionSort(self, key: str, direction: int) -> None:
        self._set_forecast_version_sort(key, direction)

    @Slot(str, int)
    def setForecastLineSort(self, key: str, direction: int) -> None:
        self._set_forecast_line_sort(key, direction)

    @Slot(str, str, str)
    def setForecastVersionFilters(
        self, search: str, status: str, generation_mode: str
    ) -> None:
        self._set_forecast_version_filters(search, status, generation_mode)

    @Slot(str, str)
    def setForecastLineFilters(self, search: str, source_type: str) -> None:
        self._set_forecast_line_filters(search, source_type)

    @Slot(str)
    def selectRateCard(self, rate_card_id: str) -> None:
        self._select_rate_card(rate_card_id)

    @Slot(int)
    def setRateCardPage(self, page: int) -> None:
        self._set_rate_card_page(page)

    @Slot(int)
    def setRateLinePage(self, page: int) -> None:
        self._set_rate_line_page(page)

    @Slot(str, int)
    def setRateCardSort(self, key: str, direction: int) -> None:
        self._set_rate_card_sort(key, direction)

    @Slot(str, int)
    def setRateLineSort(self, key: str, direction: int) -> None:
        self._set_rate_line_sort(key, direction)

    @Slot(str, str, str)
    def setRateCardFilters(self, search: str, scope: str, status: str) -> None:
        self._set_rate_card_filters(search, scope, status)

    @Slot(str, str, str, str)
    def setRateLineFilters(
        self, search: str, rate_type: str, status: str, effective_status: str
    ) -> None:
        self._set_rate_line_filters(search, rate_type, status, effective_status)

    @Slot(str)
    def selectBudgetVersion(self, budget_id: str) -> None:
        self._select_budget_version(budget_id)

    @Slot(str)
    def selectFinancialChange(self, change_id: str) -> None:
        self._select_financial_change(change_id)

    @Slot(int)
    def setFinancialChangePage(self, page: int) -> None:
        self._set_financial_change_page(page)

    @Slot(int)
    def setFinancialChangeImpactPage(self, page: int) -> None:
        self._set_financial_change_impact_page(page)

    @Slot(str, int)
    def setFinancialChangeSort(self, key: str, direction: int) -> None:
        self._set_financial_change_sort(key, direction)

    @Slot(str, int)
    def setFinancialChangeImpactSort(self, key: str, direction: int) -> None:
        self._set_financial_change_impact_sort(key, direction)

    @Slot(str, str, str, str)
    def setFinancialChangeFilters(
        self, search: str, status: str, approval_status: str, applied_state: str
    ) -> None:
        self._set_financial_change_filters(
            search, status, approval_status, applied_state
        )

    @Slot(str, str, str)
    def setFinancialChangeImpactFilters(
        self, search: str, impact_type: str, applied_state: str
    ) -> None:
        self._set_financial_change_impact_filters(search, impact_type, applied_state)

    @Slot(str)
    def selectVarianceBaseline(self, baseline_id: str) -> None:
        self._select_variance_baseline(baseline_id)

    @Slot(str)
    def selectBillingPreparation(self, preparation_id: str) -> None:
        self._select_billing_preparation(preparation_id)

    @Slot(int)
    def setBillingSchedulePage(self, page: int) -> None: self._set_billing_schedule_page(page)

    @Slot(int)
    def setBillingPreparationPage(self, page: int) -> None: self._set_billing_preparation_page(page)

    @Slot(int)
    def setBillingLinePage(self, page: int) -> None: self._set_billing_line_page(page)

    @Slot(str, int)
    def setBillingScheduleSort(self, key: str, direction: int) -> None: self._set_billing_schedule_sort(key, direction)

    @Slot(str, int)
    def setBillingPreparationSort(self, key: str, direction: int) -> None: self._set_billing_preparation_sort(key, direction)

    @Slot(str, int)
    def setBillingLineSort(self, key: str, direction: int) -> None: self._set_billing_line_sort(key, direction)

    @Slot(str, str, str)
    def setBillingScheduleFilters(self, search: str, status: str, source_state: str) -> None:
        self._set_billing_schedule_filters(search, status, source_state)

    @Slot(str, str, str, str, str, str)
    def setBillingPreparationFilters(self, search: str, status: str, method: str, approval_status: str, delivery_state: str, correction_state: str) -> None:
        self._set_billing_preparation_filters(search, status, method, approval_status, delivery_state, correction_state)

    @Slot(str, str, str)
    def setBillingLineFilters(self, search: str, source_type: str, source_state: str) -> None:
        self._set_billing_line_filters(search, source_type, source_state)

    @Slot("QVariantMap", result="QVariantMap")
    def createManualActual(self, payload: FinancialsMap) -> FinancialsMap: return self._create_manual_actual(payload)

    @Slot(str, int, int, result="QVariantMap")
    def searchFinanceProjects(self, search: str, page: int, page_size: int) -> FinancialsMap:
        return self._search_finance_projects(search, page, page_size)

    @Slot(str, int, int, result="QVariantMap")
    def searchManualActualProjects(self, search: str, page: int, page_size: int) -> FinancialsMap:
        return self._search_manual_actual_projects(search, page, page_size)

    @Slot(str, str, int, int, result="QVariantMap")
    def searchManualActualTasks(
        self, project_id: str, search: str, page: int, page_size: int
    ) -> FinancialsMap:
        return self._search_manual_actual_tasks(project_id, search, page, page_size)

    @Slot(str, str, int, int, str, result="QVariantMap")
    def searchManualActualCostCodes(
        self,
        project_id: str,
        search: str,
        page: int,
        page_size: int,
        effective_on: str,
    ) -> FinancialsMap:
        return self._search_manual_actual_cost_codes(
            project_id, search, page, page_size, effective_on
        )

    @Slot(str, result="QVariantMap")
    def resolveManualActualProject(self, project_id: str) -> FinancialsMap:
        return self._resolve_manual_actual_project(project_id)

    @Slot(str, str, result="QVariantMap")
    def resolveManualActualTask(self, project_id: str, task_id: str) -> FinancialsMap:
        return self._resolve_manual_actual_task(project_id, task_id)

    @Slot(str, str, str, result="QVariantMap")
    def resolveManualActualCostCode(
        self, project_id: str, cost_code_id: str, effective_on: str
    ) -> FinancialsMap:
        return self._resolve_manual_actual_cost_code(
            project_id, cost_code_id, effective_on
        )

    @Slot(str, str, int, int, result="QVariantMap")
    def searchBudgetTasks(
        self, project_id: str, search: str, page: int, page_size: int
    ) -> FinancialsMap:
        return self._search_budget_tasks(project_id, search, page, page_size)

    @Slot(str, str, result="QVariantMap")
    def resolveBudgetTask(self, project_id: str, task_id: str) -> FinancialsMap:
        return self._resolve_budget_task(project_id, task_id)

    @Slot(str, str, int, int, result="QVariantMap")
    def searchBudgetCostCodes(
        self, project_id: str, search: str, page: int, page_size: int
    ) -> FinancialsMap:
        return self._search_budget_cost_codes(project_id, search, page, page_size)

    @Slot(str, str, result="QVariantMap")
    def resolveBudgetCostCode(
        self, project_id: str, cost_code_id: str
    ) -> FinancialsMap:
        return self._resolve_budget_cost_code(project_id, cost_code_id)

    @Slot(str, result="QVariantMap")
    def loadManualActualDefaults(self, project_id: str) -> FinancialsMap:
        return self._load_manual_actual_defaults(project_id)

    @Slot("QVariantMap", result="QVariantMap")
    def createCostCode(self, payload: FinancialsMap) -> FinancialsMap: return self._create_cost_code(payload)

    @Slot(str, str, str, result="QVariantMap")
    def createBudgetVersion(self, project_id: str, name: str, currency: str) -> FinancialsMap:
        return self._create_budget_version(project_id, name, currency)

    @Slot(str, str, result="QVariantMap")
    def createBudgetSuccessor(self, predecessor_id: str, name: str) -> FinancialsMap:
        return self._create_budget_successor(predecessor_id, name)

    @Slot(str, int, str, str, result="QVariantMap")
    def updateBudget(self, budget_id: str, version: int, name: str, notes: str) -> FinancialsMap:
        return self._update_budget(budget_id, version, name, notes)

    @Slot(str, int, result="QVariantMap")
    def deleteBudget(self, budget_id: str, version: int) -> FinancialsMap:
        return self._delete_budget(budget_id, version)

    @Slot(str, int, str, str, str, str, str, result="QVariantMap")
    def addBudgetLine(
        self, budget_id: str, parent_version: int, cost_code_id: str,
        task_id: str, description: str, amount: str, currency: str,
    ) -> FinancialsMap:
        return self._add_budget_line(
            budget_id, parent_version, cost_code_id, task_id,
            description, amount, currency,
        )

    @Slot(str, int, int, str, str, str, str, str, result="QVariantMap")
    def updateBudgetLine(
        self, line_id: str, line_version: int, parent_version: int,
        cost_code_id: str, task_id: str, description: str,
        amount: str, currency: str,
    ) -> FinancialsMap:
        return self._update_budget_line(
            line_id, line_version, parent_version, cost_code_id,
            task_id, description, amount, currency,
        )

    @Slot(str, int, int, result="QVariantMap")
    def deleteBudgetLine(
        self, line_id: str, line_version: int, parent_version: int
    ) -> FinancialsMap:
        return self._delete_budget_line(line_id, line_version, parent_version)

    @Slot(str, int, str, result="QVariantMap")
    def submitBudget(self, budget_id: str, version: int, notes: str) -> FinancialsMap:
        return self._submit_budget(budget_id, version, notes)

    @Slot(str, int, str, result="QVariantMap")
    def requestBudgetApproval(self, budget_id: str, version: int, notes: str) -> FinancialsMap:
        return self._request_budget_approval(budget_id, version, notes)

    @Slot(str, bool, str, result="QVariantMap")
    def decideBudgetApproval(self, request_id: str, approve: bool, notes: str) -> FinancialsMap:
        return self._decide_budget_approval(request_id, approve, notes)

    @Slot(str, int, str, result="QVariantMap")
    def closeBudget(self, budget_id: str, version: int, notes: str) -> FinancialsMap:
        return self._close_budget(budget_id, version, notes)

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

    @Slot(str)
    def selectPlannedCostVersion(self, version_id: str) -> None:
        self._select_planned_cost_version(version_id)

    @Slot(int)
    def setPlannedCostVersionPage(self, page: int) -> None:
        self._set_planned_cost_version_page(page)

    @Slot(str, int)
    def setPlannedCostVersionSort(self, sort_key: str, sort_direction: int) -> None:
        self._set_planned_cost_version_sort(sort_key, sort_direction)

    @Slot(str, int)
    def setPlannedCostLineSort(self, sort_key: str, sort_direction: int) -> None:
        self._set_planned_cost_line_sort(sort_key, sort_direction)

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
