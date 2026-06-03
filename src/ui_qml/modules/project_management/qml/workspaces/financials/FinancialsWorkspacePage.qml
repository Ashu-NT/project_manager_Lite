pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "dialogs" as Dialogs
import "sections" as Sections
import "panels" as Panels
import "components" as Components

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementFinancialsWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.financialsWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({ "routeId": "project_management.financials", "title": "Financials", "summary": "Project cost, labor, baseline budget, and financial reporting workflows." })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": root.workspaceModel.title, "subtitle": root.workspaceModel.summary, "metrics": [] })
    readonly property var costsModel: root.workspaceController
        ? root.workspaceController.costs
        : ({ "title": "Cost Register", "subtitle": "Budget lines, actuals, labor, and procurement costs.", "emptyState": "Select a project to review cost control and financial exposure.", "items": [] })
    readonly property var selectedCostModel: root.workspaceController
        ? root.workspaceController.selectedCost
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "emptyState": "Select a cost item to review financial detail.", "fields": [], "state": {} })
    readonly property var cashflowModel: root.workspaceController
        ? root.workspaceController.cashflow
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var ledgerModel: root.workspaceController
        ? root.workspaceController.ledger
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var sourceAnalyticsModel: root.workspaceController
        ? root.workspaceController.sourceAnalytics
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var baselineVarianceModel: root.workspaceController
        ? (root.workspaceController.baselineVariance || []) : []

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    readonly property bool _hasProcPoCap: root.pmCatalog
        ? root.pmCatalog.hasCapability("procurement.purchase_orders.read") : false
    readonly property var _detailSections: {
        const secs = ["Budget", "Actuals", "Forecast", "Commitments", "Invoices"]
        if (root._hasProcPoCap) secs.push("Purchase Orders")
        secs.push("Earned Value")
        secs.push("Variance")
        secs.push("Activity")
        return secs
    }

    property string _tableId: "pm.financials.costs.table"
    property var _columns: []

    function _baseColumns() {
        return [
            { "key": "title",                 "label": "Description", "flex": 2,   "sortable": true,  "required": true,  "visibleByDefault": true  },
            { "key": "costCode",              "label": "Code",        "flex": 0,   "minWidth": 120, "sortable": true,  "visibleByDefault": true  },
            { "key": "statusLabel",           "label": "Cost Type",   "flex": 0,   "minWidth": 110, "type": "status",  "visibleByDefault": true  },
            { "key": "commitmentStatusLabel", "label": "Commitment",  "flex": 0,   "minWidth": 120, "type": "status",  "visibleByDefault": true  },
            { "key": "subtitle",              "label": "Task",        "flex": 1.5, "sortable": true,  "visibleByDefault": true  },
            { "key": "plannedAmountLabel",    "label": "Budget",      "flex": 0,   "minWidth": 110,   "visibleByDefault": true  },
            { "key": "forecastAmountLabel",   "label": "Forecast",    "flex": 0,   "minWidth": 110,   "visibleByDefault": true  },
            { "key": "actualAmountLabel",     "label": "Actual",      "flex": 0,   "minWidth": 110,   "visibleByDefault": true  },
            { "key": "committedAmountLabel",  "label": "Committed",   "flex": 0,   "minWidth": 110,   "visibleByDefault": false },
            { "key": "incurredDateLabel",     "label": "Date",        "flex": 0,   "minWidth": 90,    "visibleByDefault": true  }
        ]
    }

    function _applyColumnState(base, saved) {
        const order = saved ? (saved.columnOrder || []) : []
        const hidden = saved ? (saved.hiddenColumns || []) : []
        if (order.length === 0) return base.slice()
        const hiddenSet = {}
        for (let i = 0; i < hidden.length; i++) hiddenSet[hidden[i]] = true
        const byKey = {}
        for (let i = 0; i < base.length; i++) byKey[base[i].key] = base[i]
        const result = []
        for (let j = 0; j < order.length; j++) {
            const col = byKey[order[j]]
            if (!col) continue
            const c = Object.assign({}, col)
            if (c.required !== true) c.visible = !hiddenSet[order[j]]
            result.push(c)
        }
        for (let i = 0; i < base.length; i++) {
            if (order.indexOf(base[i].key) < 0) result.push(Object.assign({}, base[i]))
        }
        return result
    }

    function _buildColumnState(columns) {
        const order = []
        const hidden = []
        for (let i = 0; i < columns.length; i++) {
            order.push(columns[i].key)
            if (columns[i].visible === false) hidden.push(columns[i].key)
        }
        return { "columnOrder": order, "hiddenColumns": hidden }
    }

    Component.onCompleted: {
        const base = root._baseColumns()
        if (root.workspaceController !== null) {
            const saved = root.workspaceController.loadTableColumnState(root._tableId)
            root._columns = root._applyColumnState(base, saved)
        } else {
            root._columns = base
        }
    }

    readonly property var _detailActions: [
        { "id": "edit",   "label": "Edit",         "icon": "edit",   "enabled": true, "danger": false },
        { "id": "add",    "label": "Add Cost Line", "icon": "add",    "enabled": true, "danger": false },
        { "id": "export", "label": "Export",        "icon": "export", "enabled": true, "danger": false },
        { "id": "delete", "label": "Delete",        "icon": "delete", "enabled": true, "danger": true  }
    ]

    readonly property var _bulkChangeProperties: {
        const props = []
        const costTypeOpts = root.workspaceController ? (root.workspaceController.bulkCostTypeOptions || []) : []
        if (costTypeOpts.length > 0) props.push({ "id": "costType", "label": "Cost Type", "values": costTypeOpts })
        return props
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (detailPage) detailPage.scrollToSection(sectionIndex)
    }

    // ── Dialog host ───────────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.FinancialsDialogHost {
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                taskOptions: root.workspaceController ? (root.workspaceController.taskOptions || []) : []
                costTypeOptions: root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []
                workspaceController: root.workspaceController
                onDeleteRequested: function(costId) {
                    if (root.workspaceController !== null) root.workspaceController.deleteCostItem(costId)
                }
            }
        }
    }

    // ── Stacked layout: list page / detail page ───────────────────────────
    Item {
        anchors.fill: parent

        Item {
            anchors.fill: parent
            visible: !root._detailOpen

            Components.FinancialsListPage {
                anchors.fill: parent
                workspaceController: root.workspaceController
                overviewModel: root.overviewModel
                costsModel: root.costsModel
                columns: root._columns
                tableId: root._tableId
                bulkChangeProperties: root._bulkChangeProperties
                onRowActivated: function(rowId) { root._openDetail(0) }
                onColumnsStateChanged: function(cols) {
                    if (root.workspaceController) root.workspaceController.saveTableColumnState(root._tableId, root._buildColumnState(cols))
                    root._columns = cols
                }
                onCreateRequested: dialogHostLoader.invoke("openCreateDialog")
            }
        }

        Loader {
            id: detailPageLoader
            anchors.fill: parent
            active: root._detailOpen
            visible: root._detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent

            AppWidgets.SectionDetailPage {
                open: true
                anchors.fill: parent
                showHeader: false; showEdit: false; showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: root._detailSections
                z: 20
                Component.onCompleted: scrollToSection(root._pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root.selectedCostModel.title || "Cost Details"
                    subtitle: root.selectedCostModel.statusLabel || root.selectedCostModel.subtitle || ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions
                    onBackRequested: root._detailOpen = false
                    onActionTriggered: function(actionId) {
                        if (actionId === "edit") dialogHostLoader.invoke("openEditDialog", root.selectedCostModel)
                        else if (actionId === "add") dialogHostLoader.invoke("openCreateDialog")
                        else if (actionId === "export") { if (root.workspaceController !== null) root.workspaceController.exportFinancials() }
                        else if (actionId === "delete") dialogHostLoader.invoke("openDeleteDialog", root.selectedCostModel)
                    }
                }

                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Panels.FinancialsDetailPanel {
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    costDetail: root.selectedCostModel
                    cashflowModel: root.cashflowModel
                    ledgerModel: root.ledgerModel
                    ledgerTableModel: root.workspaceController ? root.workspaceController.ledgerTableModel : null
                    sourceAnalyticsModel: root.sourceAnalyticsModel
                    overviewModel: root.overviewModel
                    forecastModel: root.workspaceController ? root.workspaceController.forecast : ({})
                    commitmentSummaryModel: root.workspaceController ? root.workspaceController.commitmentSummary : ({})
                    baselineVarianceModel: root.baselineVarianceModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                }
            }
        }
    }
}
