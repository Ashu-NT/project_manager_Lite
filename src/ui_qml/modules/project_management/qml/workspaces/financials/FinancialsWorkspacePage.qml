pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

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
            "summary": "Project cost, labor, baseline budget, and financial reporting workflows."
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
            "emptyState": "Select a project to review cost control and financial exposure.",
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
            "emptyState": "Select a cost item to review financial detail.",
            "fields": [],
            "state": {}
        })
    readonly property var cashflowModel: root.workspaceController
        ? root.workspaceController.cashflow
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var ledgerModel: root.workspaceController
        ? root.workspaceController.ledger
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var sourceAnalyticsModel: root.workspaceController
        ? root.workspaceController.sourceAnalytics
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    readonly property var _tableColumns: [
        { "key": "title",               "label": "Description", "flex": 2,   "sortable": true  },
        { "key": "statusLabel",         "label": "Cost Type",   "flex": 0,   "minWidth": 110, "type": "status" },
        { "key": "subtitle",            "label": "Task",        "flex": 1.5, "sortable": true  },
        { "key": "plannedAmountLabel",  "label": "Budget",      "flex": 0,   "minWidth": 110  },
        { "key": "committedAmountLabel","label": "Committed",   "flex": 0,   "minWidth": 110  },
        { "key": "actualAmountLabel",   "label": "Actual",      "flex": 0,   "minWidth": 110  },
        { "key": "incurredDateLabel",   "label": "Date",        "flex": 0,   "minWidth": 90   }
    ]

    readonly property var _detailActions: [
        { "id": "edit",   "label": "Edit",         "icon": "edit",   "enabled": true, "danger": false },
        { "id": "add",    "label": "Add Cost Line", "icon": "add",    "enabled": true, "danger": false },
        { "id": "export", "label": "Export",        "icon": "export", "enabled": true, "danger": false },
        { "id": "delete", "label": "Delete",        "icon": "delete", "enabled": true, "danger": true  }
    ]

    readonly property var _bulkChangeProperties: {
        const props = []
        const costTypeOpts = root.workspaceController
            ? (root.workspaceController.bulkCostTypeOptions || [])
            : []
        if (costTypeOpts.length > 0) {
            props.push({ "id": "costType", "label": "Cost Type", "values": costTypeOpts })
        }
        return props
    }

    function _optionIndexForValue(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (detailPage) {
            detailPage.scrollToSection(sectionIndex)
        }
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            FinancialsDialogHost {
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
        }
    }

    // ── Stacked layout: list page / detail page ───────────────────────
    Item {
        anchors.fill: parent

        // ── List page (hidden when detail is open) ────────────────────
        Item {
            id: _listPage
            anchors.fill: parent
            visible: !root._detailOpen

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.KpiStrip {
                    Layout.fillWidth: true
                    metrics: root.overviewModel.metrics || []
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: (root.workspaceController ? root.workspaceController.isLoading : false)
                        && !(root.workspaceController ? root.workspaceController.isBusy : false)
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "info"
                    message: "Loading financials..."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root.workspaceController
                        ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    tone: "info"
                    message: "Saving changes..."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                AppWidgets.TableToolbar {
                    id: tableToolbar
                    Layout.fillWidth: true
                    searchText: root.workspaceController ? root.workspaceController.searchText : ""
                    searchPlaceholder: "Search cost items..."
                    showCreate: true
                    createLabel: "Add Cost"
                    showFilter: true
                    showCustomize: true
                    showViews: true
                    showRefresh: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                    }
                    onFilterClicked: filterPopup.open()
                    onCustomizeClicked: costsTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
                    onViewsClicked: viewsPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onExportRequested: {
                        if (root.workspaceController !== null) root.workspaceController.exportFinancials()
                    }
                    onCreateRequested: dialogHostLoader.invoke("openCreateDialog")
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: costsTable
                        anchors.top:    parent.top
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: _paginationBar.top
                        multiSelect: true
                        columns: root._tableColumns
                        rows: root.costsModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.costsModel.emptyState || "No cost items available."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedCostId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedCostIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectCost(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectCost(rowId)
                            root._openDetail(0)
                        }
                        onViewDetailRequested: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectCost(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setCostBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) root.workspaceController.selectVisibleCosts()
                            else root.workspaceController.clearCostBulkSelection()
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: parent.bottom
                        currentPage:  root.workspaceController ? root.workspaceController.costPage      : 1
                        pageSize:     root.workspaceController ? root.workspaceController.costPageSize   : 25
                        totalItems:   root.workspaceController ? root.workspaceController.costTotalCount : 0
                        busy:         root.workspaceController ? root.workspaceController.isBusy         : false
                        onPageRequested: function(page) {
                            if (root.workspaceController !== null) root.workspaceController.setCostPage(page)
                        }
                        onPageSizeRequested: function(pageSize) {
                            if (root.workspaceController !== null) root.workspaceController.setCostPageSize(pageSize)
                        }
                    }

                    AppWidgets.BulkActionBar {
                        id: _bulkActionBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        selectedCount: root.workspaceController ? root.workspaceController.selectedCostCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "delete",          "label": "Delete",          "icon": "delete", "danger": true,  "enabled": true },
                            { "id": "change_property", "label": "Change Cost Type","icon": "edit",   "danger": false, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null) root.workspaceController.clearCostBulkSelection()
                        }
                        onActionTriggered: function(actionId) {
                            if (actionId === "delete") {
                                root.workspaceController.bulkDeleteCosts(
                                    root.workspaceController ? (root.workspaceController.selectedCostIds || []) : []
                                )
                            } else if (actionId === "change_property") {
                                _bulkChangePropertyPopup.open()
                            }
                        }
                    }

                    AppWidgets.BulkChangePropertyPopup {
                        id: _bulkChangePropertyPopup
                        anchorItem: _bulkActionBar.actionButtonForId("change_property")
                        selectedCount: root.workspaceController ? root.workspaceController.selectedCostCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        properties: root._bulkChangeProperties

                        onApplyRequested: function(payload) {
                            if (root.workspaceController === null) return
                            if (payload.propertyId === "costType")
                                root.workspaceController.applyBulkCostType({ "value": payload.value })
                        }
                    }

                    // ── Filter popup ──────────────────────────────────────
                    AppWidgets.AnchoredPopup {
                        id: filterPopup
                        anchorItem: tableToolbar.filterButtonItem
                        width: 280
                        padding: Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color: Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: "Project"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.projectOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedProjectId : ""
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController
                                        ? (root.workspaceController.projectOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.selectProject(String(opts[index].value || ""))
                                }
                            }

                            AppControls.Label {
                                text: "Cost Type"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.costTypeOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedCostType : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController
                                        ? (root.workspaceController.costTypeOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.setCostTypeFilter(String(opts[index].value || "all"))
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "Clear"
                                    iconName: "close"
                                    onClicked: {
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.selectProject("")
                                            root.workspaceController.setCostTypeFilter("all")
                                        }
                                        filterPopup.close()
                                    }
                                }
                                AppControls.SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "Close"
                                    iconName: "close"
                                    onClicked: filterPopup.close()
                                }
                            }
                        }
                    }

                    // ── Views popup (cost type preset views) ──────────────
                    AppWidgets.AnchoredPopup {
                        id: viewsPopup
                        anchorItem: tableToolbar.viewsButtonItem
                        width: 260
                        padding: Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color: Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: "Cost View"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.costTypeOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.costTypeOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedCostType : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController
                                        ? (root.workspaceController.costTypeOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setCostTypeFilter(String(opts[index].value || "all"))
                                        viewsPopup.close()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ── Detail page (covers full area, z:20) ─────────────────────────
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
                showHeader: false
                showEdit: false
                showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: [
                    "Budget",
                    { "label": "Actuals",     "count": (root.ledgerModel.items     || []).length },
                    { "label": "Forecast",    "count": (root.cashflowModel.items    || []).length },
                    { "label": "Commitments", "count": (root.sourceAnalyticsModel.items || []).length },
                    "Invoices",
                    "Purchase Orders",
                    "Earned Value",
                    "Activity"
                ]
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
                        if (actionId === "edit") {
                            dialogHostLoader.invoke("openEditDialog", root.selectedCostModel)
                        } else if (actionId === "add") {
                            dialogHostLoader.invoke("openCreateDialog")
                        } else if (actionId === "export") {
                            if (root.workspaceController !== null) root.workspaceController.exportFinancials()
                        } else if (actionId === "delete") {
                            dialogHostLoader.invoke("openDeleteDialog", root.selectedCostModel)
                        }
                    }
                }

                FinancialsDetailSection {
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    costDetail: root.selectedCostModel
                    cashflowModel: root.cashflowModel
                    ledgerModel: root.ledgerModel
                    sourceAnalyticsModel: root.sourceAnalyticsModel
                    overviewModel: root.overviewModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                }
            }
        }
    }
}
