pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var costDetail: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "", "fields": [], "state": {}
    })
    property var cashflowModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var ledgerModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var ledgerTableModel: null
    property var sourceAnalyticsModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var overviewModel: ({ "title": "", "subtitle": "", "metrics": [] })
    property var forecastModel: ({
        "method": "", "methodLabel": "", "bacLabel": "", "acLabel": "", "evLabel": "",
        "etcLabel": "", "eacLabel": "", "vacLabel": "", "cpiLabel": "",
        "isOverBudget": false, "exceedsThreshold": false, "alertMessage": "", "metrics": []
    })
    property var commitmentSummaryModel: ({
        "plannedLabel": "", "uncommittedLabel": "", "committedLabel": "",
        "invoicedLabel": "", "paidLabel": "", "exposureLabel": "", "commitmentRatePct": 0
    })
    property var baselineVarianceModel: []
    property bool isBusy: false
    property var detailPage: null

    readonly property bool _hasCost: String(root.costDetail.id || "").length > 0
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
        if (name === "Budget")          return _sec0.implicitHeight
        if (name === "Actuals")         return _sec1.implicitHeight
        if (name === "Forecast")        return _sec2.implicitHeight
        if (name === "Commitments")     return _sec3.implicitHeight
        if (name === "Invoices")        return _sec4.implicitHeight
        if (name === "Purchase Orders") return _sec5.implicitHeight
        if (name === "Earned Value")    return _sec6.implicitHeight
        if (name === "Activity")        return _sec7.implicitHeight
        if (name === "Variance")        return _sec8.implicitHeight
        return 0
    }

    implicitHeight: _activeSectionH
    height: implicitHeight

    AppWidgets.LazySectionLoader {
        id: _sec0
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Budget")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
            FinancialsBudgetSection {
                width: parent ? parent.width : 0
                costDetail: root.costDetail
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec1
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
        id: _sec2
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Forecast")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
            FinancialsForecastSection {
                width: parent ? parent.width : 0
                forecastModel: root.forecastModel
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec3
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Commitments")
        loadingMessage: "Loading costs..."
        sourceComponent: Component {
            FinancialsCommitmentsSection {
                width: parent ? parent.width : 0
                commitmentSummaryModel: root.commitmentSummaryModel
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec4
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Invoices")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
            FinancialsInvoicesSection { width: parent ? parent.width : 0 }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec5
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Purchase Orders")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
            FinancialsPurchaseOrdersSection { width: parent ? parent.width : 0 }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec6
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Earned Value")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
            FinancialsEarnedValueSection {
                width: parent ? parent.width : 0
                forecastModel: root.forecastModel
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec7
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
        id: _sec8
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Variance")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
            FinancialsVarianceSection {
                width: parent ? parent.width : 0
                baselineVarianceModel: root.baselineVarianceModel
            }
        }
    }
}
