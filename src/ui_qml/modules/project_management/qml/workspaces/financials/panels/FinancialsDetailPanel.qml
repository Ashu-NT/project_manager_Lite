pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets
import workspaces.financials.sections 1.0

Item {
    id: root

    property var cashflowModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var ledgerModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var ledgerTableModel: null
    property var sourceAnalyticsModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var overviewModel: ({ "title": "", "subtitle": "", "metrics": [] })
    property var forecastModel: ({
        "basisLabel": "", "budgetLabel": "", "actualLabel": "",
        "etcLabel": "", "eacLabel": "", "vacLabel": "",
        "isOverBudget": false, "hasApprovedForecast": false,
        "forecastRevision": null, "forecastAsOfLabel": "", "alertMessage": "", "metrics": []
    })
    property var forecastVersionsModel: ({ "items": [] })
    property var forecastLinesModel: ({ "items": [] })
    property string selectedForecastId: ""
    property var financialChangesModel: ({ "items": [] })
    property var financialChangeImpactsModel: ({ "items": [] })
    property string selectedChangeId: ""
    property var commitmentSummaryModel: ({
        "approvedBudgetLabel": "", "postedActualLabel": "",
        "openCommitmentLabel": "", "availableAfterCommitmentLabel": "",
        "commitmentRatePct": 0
    })
    property var commitmentsModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var commitmentsTableModel: null
    property var baselineVarianceModel: []
    property var baselineVersionsModel: ({ "items": [] })
    property var varianceBasisModel: ({ "fields": [] })
    property string selectedBaselineId: ""
    property var reportBasisModel: ({ "fields": [] })
    property var financialProfileModel: ({ "id": "", "fields": [] })
    property var budgetVersionsModel: ({ "items": [] })
    property var budgetLinesModel: ({ "items": [] })
    property var rateCardsModel: ({ "items": [] })
    property var rateLinesModel: ({ "items": [] })
    property var plannedCostVersionsModel: ({ "items": [] })
    property var plannedCostLinesModel: ({ "items": [] })
    property var billingProfileModel: ({ "id": "", "fields": [] })
    property var billingScheduleModel: ({ "items": [] })
    property var billingPreparationsModel: ({ "items": [] })
    property bool isBusy: false
    property var detailPage: null
    signal configurationPageRequested(string collection, int page)
    signal forecastSelected(string forecastId)
    signal financialChangeSelected(string changeId)
    signal varianceBaselineSelected(string baselineId)

    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property var _sections: root.detailPage ? (root.detailPage.sections || []) : []

    function _secIdx(name) {
        const secs = root._sections
        for (let i = 0; i < secs.length; i++) {
            const s = secs[i]
            const sLabel = (typeof s === "string") ? s : (s.label || "")
            if (sLabel === name) return i
        }
        return -1
    }

    readonly property int _activeSectionH: {
        const secs = root._sections
        const entry = (secs.length > root._idx) ? secs[root._idx] : null
        const name = entry ? ((typeof entry === "string") ? entry : (entry.label || "")) : ""
        if (name === "Profile")         return _profile.implicitHeight
        if (name === "Budget Versions") return _budgetVersions.implicitHeight
        if (name === "Budget Lines")    return _budgetLines.implicitHeight
        if (name === "Rate Cards")      return _rateCards.implicitHeight
        if (name === "Planned Costs")   return _plannedCosts.implicitHeight
        if (name === "Actuals")         return _actuals.implicitHeight
        if (name === "Forecast")        return _forecast.implicitHeight
        if (name === "Change Control")  return _changeControl.implicitHeight
        if (name === "Commitments")     return _commitments.implicitHeight
        if (name === "Billing Preparation") return _invoices.implicitHeight
        if (name === "Purchase Orders") return _purchaseOrders.implicitHeight
        if (name === "Activity")        return _activity.implicitHeight
        if (name === "Variance")        return _variance.implicitHeight
        if (name === "Reports")         return _reports.implicitHeight
        return 0
    }

    implicitHeight: _activeSectionH
    height: implicitHeight

    AppWidgets.LazySectionLoader {
        id: _profile
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Profile")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
            FinancialsProfileSection {
                width: parent ? parent.width : 0
                profile: root.financialProfileModel
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _budgetVersions
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Budget Versions")
        loadingMessage: "Loading budget versions..."
        sourceComponent: Component {
            FinancialsBudgetVersionsSection {
                width: parent ? parent.width : 0
                versions: root.budgetVersionsModel
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _budgetLines
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Budget Lines")
        loadingMessage: "Loading budget lines..."
        sourceComponent: Component {
            FinancialsBudgetLinesSection {
                width: parent ? parent.width : 0
                lines: root.budgetLinesModel
                busy: root.isBusy
                onPageRequested: function(page) {
                    root.configurationPageRequested("budget_lines", page)
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _rateCards
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Rate Cards")
        loadingMessage: "Loading rate cards..."
        sourceComponent: Component {
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
    }

    AppWidgets.LazySectionLoader {
        id: _plannedCosts
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Planned Costs")
        loadingMessage: "Loading planned costs..."
        sourceComponent: Component {
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
    }

    AppWidgets.LazySectionLoader {
        id: _actuals
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Actuals")
        loadingMessage: "Loading costs..."
        sourceComponent: Component {
            FinancialsActualsSection {
                width: parent ? parent.width : 0
                ledgerModel: root.ledgerModel
                ledgerTableModel: root.ledgerTableModel
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _forecast
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Forecast")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
            FinancialsForecastSection {
                width: parent ? parent.width : 0
                forecastModel: root.forecastModel
                isBusy: root.isBusy
                forecastVersions: root.forecastVersionsModel
                forecastLines: root.forecastLinesModel
                selectedForecastId: root.selectedForecastId
                onForecastSelected: function(forecastId) { root.forecastSelected(forecastId) }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _changeControl
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Change Control")
        loadingMessage: "Loading financial changes..."
        sourceComponent: Component {
            FinancialsChangeSection {
                width: parent ? parent.width : 0
                changes: root.financialChangesModel
                impacts: root.financialChangeImpactsModel
                selectedChangeId: root.selectedChangeId
                onChangeSelected: function(changeId) { root.financialChangeSelected(changeId) }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _commitments
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Commitments")
        loadingMessage: "Loading costs..."
        sourceComponent: Component {
            FinancialsCommitmentsSection {
                width: parent ? parent.width : 0
                commitmentSummaryModel: root.commitmentSummaryModel
                commitmentsModel: root.commitmentsModel
                commitmentsTableModel: root.commitmentsTableModel
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _invoices
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Billing Preparation")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
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
    }

    AppWidgets.LazySectionLoader {
        id: _purchaseOrders
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Purchase Orders")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
            FinancialsPurchaseOrdersSection { width: parent ? parent.width : 0 }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _activity
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Activity")
        loadingMessage: "Loading activity..."
        sourceComponent: Component {
            FinancialsActivitySection {
                width: parent ? parent.width : 0
                ledgerModel: root.ledgerModel
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _variance
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Variance")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
            FinancialsVarianceSection {
                width: parent ? parent.width : 0
                baselineVarianceModel: root.baselineVarianceModel
                baselineVersions: root.baselineVersionsModel
                varianceBasis: root.varianceBasisModel
                selectedBaselineId: root.selectedBaselineId
                onBaselineSelected: function(baselineId) { root.varianceBaselineSelected(baselineId) }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _reports
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Reports")
        loadingMessage: "Loading report basis..."
        sourceComponent: Component {
            FinancialsReportsSection {
                width: parent ? parent.width : 0
                reportBasis: root.reportBasisModel
            }
        }
    }
}
