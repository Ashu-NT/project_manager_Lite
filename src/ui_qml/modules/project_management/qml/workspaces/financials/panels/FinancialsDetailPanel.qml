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
    property var cashflowModel: ({ "items": [] })
    property var ledgerModel: ({ "items": [] })
    property var activityModel: ({ "items": [] })
    property var ledgerTableModel: null
    property var sourceAnalyticsModel: ({ "items": [] })
    property var costTypeAnalyticsModel: ({ "items": [] })
    property var overviewModel: ({ "title": "", "subtitle": "", "metrics": [] })
    property var forecastModel: ({})
    property var forecastVersionsModel: ({ "items": [] })
    property var forecastLinesModel: ({ "items": [] })
    property string selectedForecastId: ""
    property var financialChangesModel: ({ "items": [] })
    property var financialChangeImpactsModel: ({ "items": [] })
    property string selectedChangeId: ""
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
    property string budgetVersionSortKey: "revision"
    property int budgetVersionSortDirection: Qt.DescendingOrder
    property string budgetLineSortKey: "metaText"
    property int budgetLineSortDirection: Qt.DescendingOrder
    property var rateCardsModel: ({ "items": [] })
    property var rateLinesModel: ({ "items": [] })
    property var plannedCostVersionsModel: ({ "items": [] })
    property var plannedCostLinesModel: ({ "items": [] })
    property var billingProfileModel: ({ "id": "", "fields": [] })
    property var billingScheduleModel: ({ "items": [] })
    property var billingPreparationsModel: ({ "items": [] })
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
    signal forecastSelected(string forecastId)
    signal financialChangeSelected(string changeId)
    signal varianceBaselineSelected(string baselineId)
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
            Layout.fillWidth: true
            Layout.preferredHeight: childrenRect.height
            asynchronous: true
            sourceComponent: root._activeComponent
        }
    }

    Component {
        id: overviewComponent
        FinancialsOverviewSection {
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
                onBudgetSelected: function(budgetId) { root.budgetVersionSelected(budgetId) }
                onPageRequested: function(page) { root.budgetVersionPageRequested(page) }
                onSortRequested: function(key, direction) { root.budgetVersionSortRequested(key, direction) }
            }
            FinancialsBudgetLinesSection {
                width: parent.width
                lines: root.budgetLinesModel
                tableModel: root.budgetLinesTableModel
                busy: root.isBusy
                selectedBudgetId: root.selectedBudgetId
                sortKey: root.budgetLineSortKey
                sortDirection: root.budgetLineSortDirection
                onPageRequested: function(page) {
                    root.configurationPageRequested("budget_lines", page)
                }
                onSortRequested: function(key, direction) { root.budgetLineSortRequested(key, direction) }
            }
        }
    }

    Component {
        id: plannedCostsComponent
        FinancialsPlannedCostsSection {
            width: parent ? parent.width : 0
            versions: root.plannedCostVersionsModel
            lines: root.plannedCostLinesModel
            busy: root.isBusy
            onLinePageRequested: function(page) {
                root.configurationPageRequested("planned_cost_lines", page)
            }
        }
    }

    Component {
        id: forecastComponent
        FinancialsForecastSection {
            width: parent ? parent.width : 0
            forecastModel: root.forecastModel
            isBusy: root.isBusy
            forecastVersions: root.forecastVersionsModel
            forecastLines: root.forecastLinesModel
            selectedForecastId: root.selectedForecastId
            onForecastSelected: function(forecastId) {
                root.forecastSelected(forecastId)
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
            busy: root.isBusy
            onLinePageRequested: function(page) {
                root.configurationPageRequested("rate_lines", page)
            }
        }
    }

    Component {
        id: varianceComponent
        FinancialsVarianceSection {
            width: parent ? parent.width : 0
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
            costPhasing: root.cashflowModel
            sourceAnalytics: root.sourceAnalyticsModel
            costTypeAnalytics: root.costTypeAnalyticsModel
        }
    }

    Component {
        id: reportsComponent
        FinancialsReportsSection {
            width: parent ? parent.width : 0
            reportBasis: root.reportBasisModel
        }
    }

    Component {
        id: billingComponent
        FinancialsBillingPreparationSection {
            width: parent ? parent.width : 0
            profile: root.billingProfileModel
            schedule: root.billingScheduleModel
            preparations: root.billingPreparationsModel
            onPreparationPageRequested: function(page) {
                root.configurationPageRequested("billing_preparations", page)
            }
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
            selectedChangeId: root.selectedChangeId
            onChangeSelected: function(changeId) {
                root.financialChangeSelected(changeId)
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
