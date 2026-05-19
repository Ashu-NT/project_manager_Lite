import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementFinancialsWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.financialsWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.financials",
            "title": "Financials",
            "summary": "Project cost, labor, baseline budget, and financial reporting workflows.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget financials workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var costsModel: root.workspaceController
        ? root.workspaceController.costs
        : ({
            "title": "Cost Register",
            "subtitle": "Budget lines, actuals, labor, and procurement costs.",
            "emptyState": "Project-management financials desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedCostModel: root.workspaceController
        ? root.workspaceController.selectedCost
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a cost item to review details or edit its record.",
            "fields": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    readonly property var _tableColumns: [
        { "key": "title",          "label": "Description",    "flex": 2.5, "sortable": true  },
        { "key": "statusLabel",    "label": "Type",           "flex": 0,   "minWidth": 110, "type": "status" },
        { "key": "subtitle",       "label": "Project / Task", "flex": 2,   "sortable": true  },
        { "key": "supportingText", "label": "Category",       "flex": 1.5                    },
        { "key": "metaText",       "label": "Amount",         "flex": 0,   "minWidth": 120   }
    ]

    function _projectIndexForValue(v) {
        const opts = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
        for (let i = 0; i < opts.length; i++) {
            if (String(opts[i].value || "") === String(v || "")) return i
        }
        return 0
    }

    function _costTypeIndexForValue(v) {
        const opts = root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []
        for (let i = 0; i < opts.length; i++) {
            if (String(opts[i].value || "") === String(v || "")) return i
        }
        return 0
    }

    FinancialsDialogHost {
        id: dialogHost

        selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
        taskOptions: root.workspaceController ? (root.workspaceController.taskOptions || []) : []
        costTypeOptions: root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.createCostItem(payload)
        }
        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.updateCostItem(payload)
        }
        onDeleteRequested: function(costId) {
            if (root.workspaceController !== null) root.workspaceController.deleteCostItem(costId)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        ProjectManagementWidgets.WorkspaceStateBanner {
            Layout.fillWidth: true
            isLoading: root.workspaceController ? root.workspaceController.isLoading : false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false
            errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
            feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        ProjectManagementWidgets.WorkspaceStatusSection {
            visible: false
            Layout.fillWidth: true
            migrationStatus: root.workspaceController
                ? "QML financials operations slice active"
                : (root.workspaceModel.migrationStatus || "")
            legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
            architectureStatus: "Desktop API + typed controller"
            architectureSummary: "Cost-item CRUD, finance KPI summary, cashflow, ledger trail, and analytics now run through a typed PM controller backed by the financials desktop API."
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search cost items…"
            showCreate: true
            createLabel: "Add Cost"
            showRefresh: true
            showExport: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
            }
            onRefreshRequested: {
                if (root.workspaceController !== null) root.workspaceController.refresh()
            }
            onCreateRequested: dialogHost.openCreateDialog()
        }

        // ── Cost register table with full-page detail ─────────────────
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 340
            clip: true

            AppWidgets.DataTable {
                id: costsTable
                anchors.fill: parent
                columns: root._tableColumns
                rows: root.costsModel.items || []
                selectedRowId: root.workspaceController ? root.workspaceController.selectedCostId : ""
                showFilter: true

                onFilterClicked: filterPopup.open()
                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectCost(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectCost(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectCost(rowId)
                    detailPage.open = true
                }
                onSortRequested: function(key) {}
            }

            Popup {
                id: filterPopup
                parent: costsTable
                width: 260
                padding: 12
                x: costsTable.width - width - 4
                y: 30
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                Column {
                    width: parent.width
                    spacing: 8

                    Label {
                        text: "Project"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._projectIndexForValue(
                            root.workspaceController ? root.workspaceController.selectedProjectId : ""
                        )
                        onActivated: function(index) {
                            const opt = root.workspaceController
                                ? (root.workspaceController.projectOptions || [])[index]
                                : null
                            if (opt && root.workspaceController)
                                root.workspaceController.selectProject(String(opt.value || ""))
                        }
                    }

                    Label {
                        text: "Cost Type"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._costTypeIndexForValue(
                            root.workspaceController ? root.workspaceController.selectedCostType : "all"
                        )
                        onActivated: function(index) {
                            const opt = root.workspaceController
                                ? (root.workspaceController.costTypeOptions || [])[index]
                                : null
                            if (opt && root.workspaceController)
                                root.workspaceController.setCostTypeFilter(String(opt.value || "all"))
                        }
                    }
                }
            }

            AppWidgets.RecordDetailPage {
                id: detailPage
                anchors.fill: parent
                title: root.selectedCostModel.title || "Cost Details"
                open: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onBackRequested: detailPage.open = false
                onEditRequested: dialogHost.openEditDialog(root.selectedCostModel)
                onDeleteRequested: dialogHost.openDeleteDialog(root.selectedCostModel)

                FinancialsDetailSection {
                    anchors.fill: parent
                    costDetail: root.selectedCostModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onEditRequested: dialogHost.openEditDialog(root.selectedCostModel)
                    onDeleteRequested: dialogHost.openDeleteDialog(root.selectedCostModel)
                }
            }
        }

        // ── Financial analytics panels (scrollable below the table) ───
        FinancialsInsightsSection {
            Layout.fillWidth: true
            cashflowModel: root.workspaceController ? root.workspaceController.cashflow : ({})
            ledgerModel: root.workspaceController ? root.workspaceController.ledger : ({})
            sourceAnalyticsModel: root.workspaceController ? root.workspaceController.sourceAnalytics : ({})
            costTypeAnalyticsModel: root.workspaceController ? root.workspaceController.costTypeAnalytics : ({})
            notes: root.workspaceController ? (root.workspaceController.notes || []) : []
        }

        Item { Layout.fillHeight: true }
    }
}
