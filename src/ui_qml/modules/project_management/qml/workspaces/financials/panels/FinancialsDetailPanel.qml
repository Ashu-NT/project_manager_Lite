pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import workspaces.financials.sections 1.0

Item {
    id: root

    property string activeDestination: "overview"
    property string activeSubsection: "summary"
    property var costPhasingModel: ({ "items": [] })
    property var costPhasingBasisModel: ({ "fields": [] })
    property var evmBasisModel: ({ "fields": [] })
    property var evmMetricsModel: ({ "items": [] })
    property var varianceMetricsModel: ({ "items": [] })
    property var reportDefinitionsModel: ({ "items": [] })
    property string costPhasingDateFrom: ""
    property string costPhasingDateTo: ""
    property string costPhasingGranularity: "month"
    property var ledgerModel: ({ "items": [] })
    property var activityModel: ({ "items": [] })
    property var ledgerTableModel: null
    property var overviewModel: ({ "title": "", "subtitle": "", "metrics": [] })
    property var forecastVersionsModel: ({ "items": [] })
    property var forecastLinesModel: ({ "items": [] })
    property var selectedForecastModel: ({ "id": "", "fields": [] })
    property var forecastVersionsTableModel: null
    property var forecastLinesTableModel: null
    property string selectedForecastId: ""
    property string forecastVersionSortKey: "revision"
    property int forecastVersionSortDirection: Qt.DescendingOrder
    property string forecastLineSortKey: "title"
    property int forecastLineSortDirection: Qt.AscendingOrder
    property string forecastVersionSearch: ""
    property string forecastVersionStatus: ""
    property string forecastGenerationMode: ""
    property string forecastLineSearch: ""
    property string forecastLineSourceType: ""
    property bool showGenerateForecast: false
    property bool canGenerateForecast: false
    property string generateForecastDisabledReason: ""
    property var financialChangesModel: ({ "items": [] })
    property var financialChangeImpactsModel: ({ "items": [] })
    property var selectedChangeModel: ({ "id": "", "fields": [] })
    property var financialChangesTableModel: null
    property var financialChangeImpactsTableModel: null
    property string selectedChangeId: ""
    property string changeSortKey: "metaText"
    property int changeSortDirection: Qt.DescendingOrder
    property string impactSortKey: "metaText"
    property int impactSortDirection: Qt.AscendingOrder
    property string changeSearch: ""
    property string changeStatus: ""
    property string changeApprovalStatus: ""
    property string changeAppliedState: ""
    property string impactSearch: ""
    property string impactType: ""
    property string impactAppliedState: ""
    property var commitmentSummaryModel: ({})
    property var commitmentsModel: ({ "items": [] })
    property var commitmentsTableModel: null
    property var baselineVarianceModel: []
    property var baselineVersionsModel: ({ "items": [] })
    property var varianceBasisModel: ({ "fields": [] })
    property string selectedBaselineId: ""
    property var reportBasisModel: ({ "fields": [] })
    property var financialProfileModel: ({ "id": "", "fields": [] })
    property var budgetVersionsModel: ({ "items": [] })
    property var budgetLinesModel: ({ "items": [] })
    property var budgetVersionsTableModel: null
    property var budgetLinesTableModel: null
    property string selectedBudgetId: ""
    property bool showCreateBudgetVersion: false
    property bool canCreateBudgetVersion: false
    property string createBudgetVersionDisabledReason: ""
    property string budgetVersionSortKey: "revision"
    property int budgetVersionSortDirection: Qt.DescendingOrder
    property string budgetLineSortKey: "metaText"
    property int budgetLineSortDirection: Qt.DescendingOrder
    property var rateCardsModel: ({ "items": [] })
    property var rateLinesModel: ({ "items": [] })
    property var selectedRateCardModel: ({ "id": "", "fields": [] })
    property var rateCardsTableModel: null
    property var rateLinesTableModel: null
    property string selectedRateCardId: ""
    property string rateCardSortKey: "title"
    property int rateCardSortDirection: Qt.AscendingOrder
    property string rateLineSortKey: "title"
    property int rateLineSortDirection: Qt.AscendingOrder
    property string rateCardSearch: ""
    property string rateCardScope: ""
    property string rateCardStatus: ""
    property string rateLineSearch: ""
    property string rateLineRateType: ""
    property string rateLineStatus: ""
    property string rateLineEffectiveStatus: ""
    property var plannedCostVersionsModel: ({ "items": [] })
    property var plannedCostLinesModel: ({ "items": [] })
    property var plannedCostVersionsTableModel: null
    property var plannedCostLinesTableModel: null
    property string selectedPlannedCostVersionId: ""
    property string plannedCostVersionSortKey: "revision"
    property int plannedCostVersionSortDirection: Qt.DescendingOrder
    property string plannedCostLineSortKey: "title"
    property int plannedCostLineSortDirection: Qt.AscendingOrder
    property var billingProfileModel: ({ "id": "", "fields": [] })
    property var billingScheduleModel: ({ "items": [] })
    property var billingPreparationsModel: ({ "items": [] })
    property var billingPreparationLinesModel: ({ "items": [] })
    property var selectedBillingPreparationModel: ({ "id": "", "fields": [] })
    property var billingScheduleTableModel: null
    property var billingPreparationsTableModel: null
    property var billingPreparationLinesTableModel: null
    property string selectedBillingPreparationId: ""
    property string billingScheduleSortKey: "supportingText"
    property int billingScheduleSortDirection: Qt.AscendingOrder
    property string billingPreparationSortKey: "metaText"
    property int billingPreparationSortDirection: Qt.DescendingOrder
    property string billingLineSortKey: "metaText"
    property int billingLineSortDirection: Qt.AscendingOrder
    property string billingScheduleSearch: ""
    property string billingScheduleStatus: ""
    property string billingScheduleSourceState: ""
    property string billingPreparationSearch: ""
    property string billingPreparationStatus: ""
    property string billingPreparationMethod: ""
    property string billingPreparationApprovalStatus: ""
    property string billingPreparationDeliveryState: ""
    property string billingPreparationCorrectionState: ""
    property string billingLineSearch: ""
    property string billingLineSourceType: ""
    property string billingLineSourceState: ""
    property var commercialProjectionModel: ({ "id": "", "fields": [] })
    property bool isBusy: false
    property string selectedActualEntryId: ""
    property string actualSortKey: "metaText"
    property int actualSortDirection: Qt.DescendingOrder
    property string commitmentSortKey: "metaText"
    property int commitmentSortDirection: Qt.DescendingOrder

    signal subsectionRequested(string subsection)
    signal configurationPageRequested(string collection, int page)
    signal budgetVersionSelected(string budgetId)
    signal budgetVersionPageRequested(int page)
    signal budgetVersionSortRequested(string key, int direction)
    signal budgetLineSortRequested(string key, int direction)
    signal budgetCreateRequested()
    signal budgetEditRequested(var budget)
    signal budgetSuccessorRequested(var budget)
    signal budgetLifecycleRequested(string action, var budget)
    signal budgetLineAddRequested(var budget)
    signal budgetLineEditRequested(var budget, var line)
    signal budgetLineDeleteRequested(var budget, var line)
    signal plannedCostVersionSelected(string versionId)
    signal plannedCostVersionPageRequested(int page)
    signal plannedCostVersionSortRequested(string key, int direction)
    signal plannedCostLineSortRequested(string key, int direction)
    signal forecastSelected(string forecastId)
    signal forecastVersionPageRequested(int page)
    signal forecastLinePageRequested(int page)
    signal forecastVersionSortRequested(string key, int direction)
    signal forecastLineSortRequested(string key, int direction)
    signal forecastVersionFiltersRequested(string search, string status, string generationMode)
    signal forecastLineFiltersRequested(string search, string sourceType)
    signal forecastGenerateRequested()
    signal forecastLifecycleRequested(string action, var forecast)
    signal rateCardSelected(string rateCardId)
    signal rateCardPageRequested(int page)
    signal rateLinePageRequested(int page)
    signal rateCardSortRequested(string key, int direction)
    signal rateLineSortRequested(string key, int direction)
    signal rateCardFiltersRequested(string search, string scope, string status)
    signal rateLineFiltersRequested(string search, string rateType, string status, string effectiveStatus)
    signal financialChangeSelected(string changeId)
    signal financialChangePageRequested(int page)
    signal financialChangeImpactPageRequested(int page)
    signal financialChangeSortRequested(string key, int direction)
    signal financialChangeImpactSortRequested(string key, int direction)
    signal financialChangeFiltersRequested(string search, string status, string approvalStatus, string appliedState)
    signal financialChangeImpactFiltersRequested(string search, string impactType, string appliedState)
    signal varianceBaselineSelected(string baselineId)
    signal costPhasingPresetRequested(int months, string granularity)
    signal billingPreparationSelected(string preparationId)
    signal billingSchedulePageRequested(int page)
    signal billingPreparationPageRequested(int page)
    signal billingLinePageRequested(int page)
    signal billingScheduleSortRequested(string key, int direction)
    signal billingPreparationSortRequested(string key, int direction)
    signal billingLineSortRequested(string key, int direction)
    signal billingScheduleFiltersRequested(string search, string status, string sourceState)
    signal billingPreparationFiltersRequested(string search, string status, string method, string approvalStatus, string deliveryState, string correctionState)
    signal billingLineFiltersRequested(string search, string sourceType, string sourceState)
    signal actualEntrySelected(string entryId)
    signal actualPageRequested(int page)
    signal actualPageSizeRequested(int pageSize)
    signal actualSortRequested(string key, int direction)
    signal commitmentPageRequested(int page)
    signal commitmentPageSizeRequested(int pageSize)
    signal commitmentSortRequested(string key, int direction)

    readonly property var _tabs: {
        if (root.activeDestination === "planning") return [
            { "id": "budgets", "label": "Budgets" },
            { "id": "planned_costs", "label": "Planned Costs" },
            { "id": "forecast", "label": "Forecast" }
        ]
        if (root.activeDestination === "costs") return [
            { "id": "actuals", "label": "Actuals" },
            { "id": "commitments", "label": "Commitments" },
            { "id": "rates", "label": "Rate Cards" }
        ]
        if (root.activeDestination === "performance") return [
            { "id": "evm", "label": "EVM" },
            { "id": "variance", "label": "Variance" },
            { "id": "cost_phasing", "label": "Cost Phasing" },
            { "id": "reports", "label": "Reports" }
        ]
        if (root.activeDestination === "commercial") return [
            { "id": "billing", "label": "Billing Preparation" },
            { "id": "profitability", "label": "Projected Profitability" },
            { "id": "accounting", "label": "Accounting Status" }
        ]
        if (root.activeDestination === "controls") return [
            { "id": "setup", "label": "Financial Setup" },
            { "id": "changes", "label": "Change Control" },
            { "id": "activity", "label": "Activity" }
        ]
        return [{ "id": "summary", "label": "Summary" }]
    }

    readonly property int _tabIndex: {
        for (let index = 0; index < root._tabs.length; index += 1) {
            if (String(root._tabs[index].id) === root.activeSubsection) return index
        }
        return 0
    }

    readonly property Component _activeComponent: {
        const key = root.activeDestination + ":" + root.activeSubsection
        if (key === "overview:summary") return overviewComponent
        if (key === "planning:budgets") return budgetsComponent
        if (key === "planning:planned_costs") return plannedCostsComponent
        if (key === "planning:forecast") return forecastComponent
        if (key === "costs:actuals") return actualsComponent
        if (key === "costs:commitments") return commitmentsComponent
        if (key === "costs:rates") return ratesComponent
        if (key === "performance:evm") return evmComponent
        if (key === "performance:variance") return varianceComponent
        if (key === "performance:cost_phasing") return costPhasingComponent
        if (key === "performance:reports") return reportsComponent
        if (key === "commercial:billing") return billingComponent
        if (key === "commercial:profitability") return profitabilityComponent
        if (key === "commercial:accounting") return accountingComponent
        if (key === "controls:setup") return profileComponent
        if (key === "controls:changes") return changesComponent
        if (key === "controls:activity") return activityComponent
        return overviewComponent
    }

    implicitHeight: contentColumn.implicitHeight
    height: implicitHeight

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.DetailTabBar {
            Layout.fillWidth: true
            visible: root._tabs.length > 1
            tabs: root._tabs
            currentIndex: root._tabIndex
            onTabSelected: function(index) {
                const tab = root._tabs[index]
                if (tab) root.subsectionRequested(String(tab.id || ""))
            }
        }

        Loader {
            id: destinationLoader
            objectName: "financialsDestinationLoader"
            readonly property Item loadedDestination: item as Item
            Layout.fillWidth: true
            Layout.preferredHeight: loadedDestination ? loadedDestination.implicitHeight : 0
            asynchronous: true
            sourceComponent: root._activeComponent
        }
    }

    Component {
        id: overviewComponent
        FinancialsOverviewSection {
            objectName: "financialsOverviewSection"
            width: parent ? parent.width : 0
            overview: root.overviewModel
        }
    }

    Component {
        id: budgetsComponent
        Column {
            width: parent ? parent.width : 0
            spacing: Theme.AppTheme.spacingLg
            FinancialsBudgetVersionsSection {
                width: parent.width
                versions: root.budgetVersionsModel
                tableModel: root.budgetVersionsTableModel
                busy: root.isBusy
                selectedBudgetId: root.selectedBudgetId
                sortKey: root.budgetVersionSortKey
                sortDirection: root.budgetVersionSortDirection
                showCreateVersion: root.showCreateBudgetVersion
                canCreateVersion: root.canCreateBudgetVersion
                createVersionDisabledReason: root.createBudgetVersionDisabledReason
                onBudgetSelected: function(budgetId) { root.budgetVersionSelected(budgetId) }
                onPageRequested: function(page) { root.budgetVersionPageRequested(page) }
                onSortRequested: function(key, direction) { root.budgetVersionSortRequested(key, direction) }
                onCreateVersionRequested: root.budgetCreateRequested()
                onEditRequested: function(budget) { root.budgetEditRequested(budget) }
                onSuccessorRequested: function(budget) { root.budgetSuccessorRequested(budget) }
                onLifecycleRequested: function(action, budget) {
                    root.budgetLifecycleRequested(action, budget)
                }
            }
            FinancialsBudgetLinesSection {
                width: parent.width
                lines: root.budgetLinesModel
                tableModel: root.budgetLinesTableModel
                busy: root.isBusy
                selectedBudgetId: root.selectedBudgetId
                selectedBudget: {
                    const items = root.budgetVersionsModel.items || []
                    for (let index = 0; index < items.length; index += 1) {
                        if (String(items[index].id || "") === root.selectedBudgetId)
                            return items[index]
                    }
                    return null
                }
                sortKey: root.budgetLineSortKey
                sortDirection: root.budgetLineSortDirection
                onPageRequested: function(page) {
                    root.configurationPageRequested("budget_lines", page)
                }
                onSortRequested: function(key, direction) { root.budgetLineSortRequested(key, direction) }
                onAddRequested: function(budget) { root.budgetLineAddRequested(budget) }
                onEditRequested: function(budget, line) {
                    root.budgetLineEditRequested(budget, line)
                }
                onDeleteRequested: function(budget, line) {
                    root.budgetLineDeleteRequested(budget, line)
                }
            }
        }
    }

    Component {
        id: plannedCostsComponent
        FinancialsPlannedCostsSection {
            width: parent ? parent.width : 0
            versions: root.plannedCostVersionsModel
            lines: root.plannedCostLinesModel
            versionsTableModel: root.plannedCostVersionsTableModel
            linesTableModel: root.plannedCostLinesTableModel
            busy: root.isBusy
            selectedVersionId: root.selectedPlannedCostVersionId
            versionSortKey: root.plannedCostVersionSortKey
            versionSortDirection: root.plannedCostVersionSortDirection
            lineSortKey: root.plannedCostLineSortKey
            lineSortDirection: root.plannedCostLineSortDirection
            onVersionSelected: function(versionId) {
                root.plannedCostVersionSelected(versionId)
            }
            onVersionPageRequested: function(page) {
                root.plannedCostVersionPageRequested(page)
            }
            onLinePageRequested: function(page) {
                root.configurationPageRequested("planned_cost_lines", page)
            }
            onVersionSortRequested: function(key, direction) {
                root.plannedCostVersionSortRequested(key, direction)
            }
            onLineSortRequested: function(key, direction) {
                root.plannedCostLineSortRequested(key, direction)
            }
        }
    }

    Component {
        id: forecastComponent
        FinancialsForecastSection {
            width: parent ? parent.width : 0
            isBusy: root.isBusy
            forecastVersions: root.forecastVersionsModel
            forecastLines: root.forecastLinesModel
            selectedForecast: root.selectedForecastModel
            versionsTableModel: root.forecastVersionsTableModel
            linesTableModel: root.forecastLinesTableModel
            selectedForecastId: root.selectedForecastId
            versionSortKey: root.forecastVersionSortKey
            versionSortDirection: root.forecastVersionSortDirection
            lineSortKey: root.forecastLineSortKey
            lineSortDirection: root.forecastLineSortDirection
            versionSearch: root.forecastVersionSearch
            versionStatus: root.forecastVersionStatus
            generationMode: root.forecastGenerationMode
            lineSearch: root.forecastLineSearch
            lineSourceType: root.forecastLineSourceType
            showGenerate: root.showGenerateForecast
            canGenerate: root.canGenerateForecast
            generateDisabledReason: root.generateForecastDisabledReason
            onGenerateRequested: root.forecastGenerateRequested()
            onLifecycleRequested: function(action, forecast) {
                root.forecastLifecycleRequested(action, forecast)
            }
            onForecastSelected: function(forecastId) {
                root.forecastSelected(forecastId)
            }
            onVersionPageRequested: function(page) { root.forecastVersionPageRequested(page) }
            onLinePageRequested: function(page) { root.forecastLinePageRequested(page) }
            onVersionSortRequested: function(key, direction) {
                root.forecastVersionSortRequested(key, direction)
            }
            onLineSortRequested: function(key, direction) {
                root.forecastLineSortRequested(key, direction)
            }
            onVersionFiltersRequested: function(search, status, generationMode) {
                root.forecastVersionFiltersRequested(search, status, generationMode)
            }
            onLineFiltersRequested: function(search, sourceType) {
                root.forecastLineFiltersRequested(search, sourceType)
            }
        }
    }

    Component {
        id: actualsComponent
        FinancialsActualsSection {
            width: parent ? parent.width : 0
            ledgerModel: root.ledgerModel
            ledgerTableModel: root.ledgerTableModel
            isBusy: root.isBusy
            selectedEntryId: root.selectedActualEntryId
            sortKey: root.actualSortKey
            sortDirection: root.actualSortDirection
            onEntrySelected: function(entryId) { root.actualEntrySelected(entryId) }
            onPageRequested: function(page) { root.actualPageRequested(page) }
            onPageSizeRequested: function(pageSize) { root.actualPageSizeRequested(pageSize) }
            onSortRequested: function(key, direction) { root.actualSortRequested(key, direction) }
        }
    }

    Component {
        id: commitmentsComponent
        FinancialsCommitmentsSection {
            width: parent ? parent.width : 0
            commitmentSummaryModel: root.commitmentSummaryModel
            commitmentsModel: root.commitmentsModel
            commitmentsTableModel: root.commitmentsTableModel
            isBusy: root.isBusy
            sortKey: root.commitmentSortKey
            sortDirection: root.commitmentSortDirection
            onPageRequested: function(page) { root.commitmentPageRequested(page) }
            onPageSizeRequested: function(pageSize) { root.commitmentPageSizeRequested(pageSize) }
            onSortRequested: function(key, direction) { root.commitmentSortRequested(key, direction) }
        }
    }

    Component {
        id: ratesComponent
        FinancialsRateCardsSection {
            width: parent ? parent.width : 0
            cards: root.rateCardsModel
            lines: root.rateLinesModel
            selectedCard: root.selectedRateCardModel
            cardsTableModel: root.rateCardsTableModel
            linesTableModel: root.rateLinesTableModel
            selectedCardId: root.selectedRateCardId
            cardSortKey: root.rateCardSortKey
            cardSortDirection: root.rateCardSortDirection
            lineSortKey: root.rateLineSortKey
            lineSortDirection: root.rateLineSortDirection
            cardSearch: root.rateCardSearch
            cardScope: root.rateCardScope
            cardStatus: root.rateCardStatus
            lineSearch: root.rateLineSearch
            lineRateType: root.rateLineRateType
            lineStatus: root.rateLineStatus
            lineEffectiveStatus: root.rateLineEffectiveStatus
            busy: root.isBusy
            onCardSelected: function(rateCardId) { root.rateCardSelected(rateCardId) }
            onCardPageRequested: function(page) { root.rateCardPageRequested(page) }
            onLinePageRequested: function(page) { root.rateLinePageRequested(page) }
            onCardSortRequested: function(key, direction) { root.rateCardSortRequested(key, direction) }
            onLineSortRequested: function(key, direction) { root.rateLineSortRequested(key, direction) }
            onCardFiltersRequested: function(search, scope, status) {
                root.rateCardFiltersRequested(search, scope, status)
            }
            onLineFiltersRequested: function(search, rateType, status, effectiveStatus) {
                root.rateLineFiltersRequested(search, rateType, status, effectiveStatus)
            }
        }
    }

    Component {
        id: evmComponent
        FinancialsEvmSection {
            width: parent ? parent.width : 0
            basis: root.evmBasisModel
            metrics: root.evmMetricsModel
        }
    }

    Component {
        id: varianceComponent
        FinancialsVarianceSection {
            width: parent ? parent.width : 0
            varianceMetrics: root.varianceMetricsModel
            baselineVarianceModel: root.baselineVarianceModel
            baselineVersions: root.baselineVersionsModel
            varianceBasis: root.varianceBasisModel
            selectedBaselineId: root.selectedBaselineId
            onBaselineSelected: function(baselineId) {
                root.varianceBaselineSelected(baselineId)
            }
        }
    }

    Component {
        id: costPhasingComponent
        FinancialsCostPhasingSection {
            width: parent ? parent.width : 0
            costPhasing: root.costPhasingModel
            basis: root.costPhasingBasisModel
            dateFrom: root.costPhasingDateFrom
            dateTo: root.costPhasingDateTo
            granularity: root.costPhasingGranularity
            onPresetRequested: function(months, granularity) {
                root.costPhasingPresetRequested(months, granularity)
            }
        }
    }

    Component {
        id: reportsComponent
        FinancialsReportsSection {
            width: parent ? parent.width : 0
            reportBasis: root.reportBasisModel
            reportDefinitions: root.reportDefinitionsModel
        }
    }

    Component {
        id: billingComponent
        FinancialsBillingPreparationSection {
            width: parent ? parent.width : 0
            profile: root.billingProfileModel
            schedule: root.billingScheduleModel
            preparations: root.billingPreparationsModel
            lines: root.billingPreparationLinesModel
            selectedPreparation: root.selectedBillingPreparationModel
            scheduleTableModel: root.billingScheduleTableModel
            preparationsTableModel: root.billingPreparationsTableModel
            linesTableModel: root.billingPreparationLinesTableModel
            selectedPreparationId: root.selectedBillingPreparationId
            scheduleSortKey: root.billingScheduleSortKey
            scheduleSortDirection: root.billingScheduleSortDirection
            preparationSortKey: root.billingPreparationSortKey
            preparationSortDirection: root.billingPreparationSortDirection
            lineSortKey: root.billingLineSortKey
            lineSortDirection: root.billingLineSortDirection
            scheduleSearch: root.billingScheduleSearch
            scheduleStatus: root.billingScheduleStatus
            scheduleSourceState: root.billingScheduleSourceState
            preparationSearch: root.billingPreparationSearch
            preparationStatus: root.billingPreparationStatus
            preparationMethod: root.billingPreparationMethod
            preparationApprovalStatus: root.billingPreparationApprovalStatus
            preparationDeliveryState: root.billingPreparationDeliveryState
            preparationCorrectionState: root.billingPreparationCorrectionState
            lineSearch: root.billingLineSearch
            lineSourceType: root.billingLineSourceType
            lineSourceState: root.billingLineSourceState
            busy: root.isBusy
            onPreparationSelected: function(id) { root.billingPreparationSelected(id) }
            onSchedulePageRequested: function(page) { root.billingSchedulePageRequested(page) }
            onPreparationPageRequested: function(page) { root.billingPreparationPageRequested(page) }
            onLinePageRequested: function(page) { root.billingLinePageRequested(page) }
            onScheduleSortRequested: function(key, direction) { root.billingScheduleSortRequested(key, direction) }
            onPreparationSortRequested: function(key, direction) { root.billingPreparationSortRequested(key, direction) }
            onLineSortRequested: function(key, direction) { root.billingLineSortRequested(key, direction) }
            onScheduleFiltersRequested: function(search, status, sourceState) { root.billingScheduleFiltersRequested(search, status, sourceState) }
            onPreparationFiltersRequested: function(search, status, method, approvalStatus, deliveryState, correctionState) { root.billingPreparationFiltersRequested(search, status, method, approvalStatus, deliveryState, correctionState) }
            onLineFiltersRequested: function(search, sourceType, sourceState) { root.billingLineFiltersRequested(search, sourceType, sourceState) }
        }
    }

    Component {
        id: profitabilityComponent
        FinancialsCommercialProjectionSection {
            width: parent ? parent.width : 0
            projection: root.commercialProjectionModel
        }
    }

    Component {
        id: accountingComponent
        Column {
            objectName: "financialsAccountingSection"
            width: parent ? parent.width : 0
            spacing: Theme.AppTheme.spacingMd
            AppWidgets.SectionHeading {
                width: parent.width
                label: "Accounting Status"
            }
            AppWidgets.InlineMessage {
                width: parent.width
                tone: "info"
                message: "Accounting owns invoice, receivable, payment, and statutory truth. PM displays only externally acknowledged outcomes."
            }
            FinancialsCollectionBlock {
                width: parent.width
                collection: root.billingPreparationsModel
                busy: root.isBusy
                onPageRequested: function(page) {
                    root.configurationPageRequested("billing_preparations", page)
                }
            }
        }
    }

    Component {
        id: profileComponent
        FinancialsProfileSection {
            width: parent ? parent.width : 0
            profile: root.financialProfileModel
        }
    }

    Component {
        id: changesComponent
        FinancialsChangeSection {
            width: parent ? parent.width : 0
            changes: root.financialChangesModel
            impacts: root.financialChangeImpactsModel
            selectedChange: root.selectedChangeModel
            changesTableModel: root.financialChangesTableModel
            impactsTableModel: root.financialChangeImpactsTableModel
            selectedChangeId: root.selectedChangeId
            changeSortKey: root.changeSortKey
            changeSortDirection: root.changeSortDirection
            impactSortKey: root.impactSortKey
            impactSortDirection: root.impactSortDirection
            changeSearch: root.changeSearch
            changeStatus: root.changeStatus
            changeApprovalStatus: root.changeApprovalStatus
            changeAppliedState: root.changeAppliedState
            impactSearch: root.impactSearch
            impactType: root.impactType
            impactAppliedState: root.impactAppliedState
            busy: root.isBusy
            onChangeSelected: function(changeId) {
                root.financialChangeSelected(changeId)
            }
            onChangePageRequested: function(page) { root.financialChangePageRequested(page) }
            onImpactPageRequested: function(page) { root.financialChangeImpactPageRequested(page) }
            onChangeSortRequested: function(key, direction) { root.financialChangeSortRequested(key, direction) }
            onImpactSortRequested: function(key, direction) { root.financialChangeImpactSortRequested(key, direction) }
            onChangeFiltersRequested: function(search, status, approvalStatus, appliedState) {
                root.financialChangeFiltersRequested(search, status, approvalStatus, appliedState)
            }
            onImpactFiltersRequested: function(search, impactType, appliedState) {
                root.financialChangeImpactFiltersRequested(search, impactType, appliedState)
            }
        }
    }

    Component {
        id: activityComponent
        FinancialsActivitySection {
            width: parent ? parent.width : 0
            activityModel: root.activityModel
        }
    }
}
