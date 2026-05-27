pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers

AppLayouts.WorkspaceFrame {
    id: root

    property var platformCatalog
    property var _caps: ({})

    Component.onCompleted: {
        if (root.platformCatalog) {
            root._caps = root.platformCatalog.capabilitySnapshot()
        }
    }

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementProcurementWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.procurementWorkspace
        : null

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": "Procurement", "subtitle": "Requisitions, purchase orders, receiving, and supplier fulfillment.", "metrics": [] })
    readonly property var requisitionsModel: root.workspaceController
        ? root.workspaceController.requisitions
        : ({ "items": [], "emptyState": "No requisitions found." })
    readonly property var purchaseOrdersModel: root.workspaceController
        ? root.workspaceController.purchaseOrders
        : ({ "items": [], "emptyState": "No purchase orders found." })
    readonly property var selectedRequisitionModel: root.workspaceController
        ? root.workspaceController.selectedRequisition
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "fields": [], "state": {} })
    readonly property var selectedPurchaseOrderModel: root.workspaceController
        ? root.workspaceController.selectedPurchaseOrder
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "fields": [], "state": {} })

    readonly property bool _isRequisitionsView: root.workspaceController
        ? root.workspaceController.activeView === "requisitions"
        : true

    title: root.overviewModel.title || "Procurement"
    subtitle: root.overviewModel.subtitle || ""

    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var _detailPage: _detailPageLoader.item

    readonly property var _requisitionColumns: [
        { "key": "title",       "label": "Requisition",  "flex": 2,   "sortable": true },
        { "key": "subtitle",    "label": "Site / Dept",  "flex": 1.5 },
        { "key": "statusLabel", "label": "Status",       "flex": 0,   "minWidth": 90, "type": "status" },
        { "key": "metaText",    "label": "Date / Ref",   "flex": 1 }
    ]
    readonly property var _purchaseOrderColumns: [
        { "key": "title",       "label": "Purchase Order", "flex": 2,  "sortable": true },
        { "key": "subtitle",    "label": "Supplier",       "flex": 1.5 },
        { "key": "statusLabel", "label": "Status",         "flex": 0,  "minWidth": 90, "type": "status" },
        { "key": "metaText",    "label": "Date / Value",   "flex": 1 }
    ]

    readonly property var _detailSections: root._isRequisitionsView
        ? ["Overview", "Lines", "Activity"]
        : ["Overview", "Lines", "Receipts", "Activity"]

    readonly property var _detailActions: {
        const idx = root._detailPage ? root._detailPage.activeSectionIndex : 0
        if (idx !== 0) return []
        if (root._isRequisitionsView) {
            const state = root.selectedRequisitionModel.state || {}
            const actions = []
            if (state.canEdit)   actions.push({ "id": "edit",   "label": "Edit",   "icon": "edit",   "enabled": true, "danger": false })
            if (state.canSubmit) actions.push({ "id": "submit", "label": "Submit", "icon": "approve","enabled": true, "danger": false })
            if (state.canCancel) actions.push({ "id": "cancel", "label": "Cancel", "icon": "reject", "enabled": true, "danger": true  })
            return actions
        } else {
            const state = root.selectedPurchaseOrderModel.state || {}
            const actions = []
            if (state.canEdit)    actions.push({ "id": "edit",    "label": "Edit",    "icon": "edit",        "enabled": true, "danger": false })
            if (state.canSubmit)  actions.push({ "id": "submit",  "label": "Submit",  "icon": "approve",     "enabled": true, "danger": false })
            if (state.canSend)    actions.push({ "id": "send",    "label": "Send",    "icon": "arrow_right", "enabled": true, "danger": false })
            if (state.canReceipt) actions.push({ "id": "receipt", "label": "Receive", "icon": "add",         "enabled": true, "danger": false })
            if (state.canClose)   actions.push({ "id": "close",   "label": "Close",   "icon": "check",       "enabled": true, "danger": false })
            if (state.canCancel)  actions.push({ "id": "cancel",  "label": "Cancel",  "icon": "reject",      "enabled": true, "danger": true  })
            return actions
        }
    }

    function _optionIndexForValue(options, value) {
        const optList = options || []
        for (let i = 0; i < optList.length; i++) {
            if (String(optList[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (root._detailPage) root._detailPage.scrollToSection(sectionIndex)
    }

    // ── Dialog host ────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            ProcurementDialogHost {
                siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                supplierOptions: root.workspaceController ? (root.workspaceController.supplierOptions || []) : []
                itemOptions: root.workspaceController ? (root.workspaceController.itemOptions || []) : []
                requisitionOptions: root.workspaceController ? (root.workspaceController.requisitionOptions || []) : []
                requisitionLineOptions: root.workspaceController ? (root.workspaceController.requisitionLineOptions || []) : []

                onCreateRequisitionRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createRequisition(payload)
                }
                onUpdateRequisitionRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updateRequisition(payload)
                }
                onAddRequisitionLineRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.addRequisitionLine(payload)
                }
                onCreatePurchaseOrderRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createPurchaseOrder(payload)
                }
                onUpdatePurchaseOrderRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updatePurchaseOrder(payload)
                }
                onAddPurchaseOrderLineRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.addPurchaseOrderLine(payload)
                }
                onPostReceiptRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.postReceipt(payload)
                }
            }
        }
    }

    // ── Stacked list / detail ──────────────────────────────────────
    Item {
        anchors.fill: parent

        // ── List page ──────────────────────────────────────────────
        Item {
            anchors.fill: parent
            visible: !root._detailOpen || _detailPageLoader.status !== Loader.Ready

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
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "info"
                    message: "Loading procurement..."
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
                    searchPlaceholder: root._isRequisitionsView ? "Search requisitions..." : "Search purchase orders..."
                    showCreate: true
                    createLabel: root._isRequisitionsView ? "New Requisition" : "New PO"
                    showFilter: true
                    showViews: true
                    showRefresh: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                    }
                    onFilterClicked: filterPopup.open()
                    onViewsClicked: viewsPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onExportRequested: {}
                    onCreateRequested: {
                        if (root._isRequisitionsView) {
                            dialogHostLoader.invoke("openCreateRequisitionDialog",
                                root.workspaceController ? root.workspaceController.selectedSiteFilter : "all",
                                root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all")
                        } else {
                            dialogHostLoader.invoke("openCreatePurchaseOrderDialog",
                                root.selectedRequisitionModel,
                                root.workspaceController ? root.workspaceController.selectedSiteFilter : "all")
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: _requisitionsTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: _paginationBar.top
                        visible: root._isRequisitionsView
                        multiSelect: true
                        columns: root._requisitionColumns
                        rows: root.requisitionsModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.requisitionsModel.emptyState || "No requisitions found."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedRequisitionId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedRequisitionIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectRequisition(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateRequisition(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null) root.workspaceController.setRequisitionBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) root.workspaceController.selectVisibleRequisitions()
                            else root.workspaceController.clearRequisitionBulkSelection()
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.DataTable {
                        id: _purchaseOrdersTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: _paginationBar.top
                        visible: !root._isRequisitionsView
                        multiSelect: true
                        columns: root._purchaseOrderColumns
                        rows: root.purchaseOrdersModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.purchaseOrdersModel.emptyState || "No purchase orders found."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedPurchaseOrderId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedPurchaseOrderIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectPurchaseOrder(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activatePurchaseOrder(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null) root.workspaceController.setPurchaseOrderBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) root.workspaceController.selectVisiblePurchaseOrders()
                            else root.workspaceController.clearPurchaseOrderBulkSelection()
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        currentPage: root._isRequisitionsView
                            ? (root.workspaceController ? root.workspaceController.requisitionPage : 1)
                            : (root.workspaceController ? root.workspaceController.purchaseOrderPage : 1)
                        pageSize: root._isRequisitionsView
                            ? (root.workspaceController ? root.workspaceController.requisitionPageSize : 25)
                            : (root.workspaceController ? root.workspaceController.purchaseOrderPageSize : 25)
                        totalItems: root._isRequisitionsView
                            ? (root.workspaceController ? root.workspaceController.requisitionTotalCount : 0)
                            : (root.workspaceController ? root.workspaceController.purchaseOrderTotalCount : 0)
                        busy: root.workspaceController ? root.workspaceController.isBusy : false

                        onPageRequested: function(page) {
                            if (root.workspaceController === null) return
                            if (root._isRequisitionsView) root.workspaceController.setRequisitionPage(page)
                            else root.workspaceController.setPurchaseOrderPage(page)
                        }
                        onPageSizeRequested: function(size) {
                            if (root.workspaceController === null) return
                            if (root._isRequisitionsView) root.workspaceController.setRequisitionPageSize(size)
                            else root.workspaceController.setPurchaseOrderPageSize(size)
                        }
                    }

                    // ── Filter popup ───────────────────────────────
                    AppWidgets.AnchoredPopup {
                        id: filterPopup
                        anchorItem: tableToolbar.filterButtonItem
                        width: 304
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
                                text: "Site"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.siteOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setSiteFilter(String(opts[index].value || "all"))
                                    }
                                }
                            }

                            AppControls.Label {
                                text: "Supplier"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                                visible: !root._isRequisitionsView
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                visible: !root._isRequisitionsView
                                model: root.workspaceController ? (root.workspaceController.supplierOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.supplierOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedSupplierFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.supplierOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setSupplierFilter(String(opts[index].value || "all"))
                                    }
                                }
                            }

                            AppControls.Label {
                                text: root._isRequisitionsView ? "Requisition Status" : "PO Status"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root._isRequisitionsView
                                    ? (root.workspaceController ? (root.workspaceController.requisitionStatusOptions || []) : [])
                                    : (root.workspaceController ? (root.workspaceController.purchaseOrderStatusOptions || []) : [])
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root._isRequisitionsView
                                        ? (root.workspaceController ? (root.workspaceController.requisitionStatusOptions || []) : [])
                                        : (root.workspaceController ? (root.workspaceController.purchaseOrderStatusOptions || []) : []),
                                    root._isRequisitionsView
                                        ? (root.workspaceController ? root.workspaceController.selectedRequisitionStatusFilter : "all")
                                        : (root.workspaceController ? root.workspaceController.selectedPurchaseOrderStatusFilter : "all")
                                )
                                onActivated: function(index) {
                                    if (root.workspaceController === null) return
                                    const opts = root._isRequisitionsView
                                        ? (root.workspaceController.requisitionStatusOptions || [])
                                        : (root.workspaceController.purchaseOrderStatusOptions || [])
                                    if (!opts[index]) return
                                    if (root._isRequisitionsView) {
                                        root.workspaceController.setRequisitionStatusFilter(String(opts[index].value || "all"))
                                    } else {
                                        root.workspaceController.setPurchaseOrderStatusFilter(String(opts[index].value || "all"))
                                    }
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
                                        if (root.workspaceController !== null) root.workspaceController.clearFilters()
                                        filterPopup.close()
                                    }
                                }
                                AppControls.PrimaryButton {
                                    Layout.fillWidth: true
                                    text: "Apply"
                                    iconName: "filter"
                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                    onClicked: filterPopup.close()
                                }
                            }
                        }
                    }

                    // ── Views popup ────────────────────────────────
                    AppWidgets.AnchoredPopup {
                        id: viewsPopup
                        anchorItem: tableToolbar.viewsButtonItem
                        width: 220
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
                                text: "View"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            AppControls.PrimaryButton {
                                Layout.fillWidth: true
                                text: "Requisitions"
                                iconName: "register"
                                enabled: !root._isRequisitionsView
                                onClicked: {
                                    if (root.workspaceController !== null) root.workspaceController.setActiveView("requisitions")
                                    viewsPopup.close()
                                }
                            }
                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text: "Purchase Orders"
                                iconName: "procurement"
                                enabled: root._isRequisitionsView
                                onClicked: {
                                    if (root.workspaceController !== null) root.workspaceController.setActiveView("purchase_orders")
                                    viewsPopup.close()
                                }
                            }
                        }
                    }

                    // ── Bulk action bar ────────────────────────────
                    AppWidgets.BulkActionBar {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        visible: root._isRequisitionsView
                        selectedCount: root.workspaceController ? root.workspaceController.selectedRequisitionCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "cancel", "label": "Cancel Selected", "icon": "reject", "danger": true, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null) root.workspaceController.clearRequisitionBulkSelection()
                        }
                        onActionTriggered: function(actionId) {}
                    }

                    AppWidgets.BulkActionBar {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        visible: !root._isRequisitionsView
                        selectedCount: root.workspaceController ? root.workspaceController.selectedPurchaseOrderCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "cancel", "label": "Cancel Selected", "icon": "reject", "danger": true, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null) root.workspaceController.clearPurchaseOrderBulkSelection()
                        }
                        onActionTriggered: function(actionId) {}
                    }
                }
            }
        }

        // ── Detail page (lazy loaded) ──────────────────────────────
        Loader {
            id: _detailPageLoader
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
                sections: root._detailSections
                z: 20

                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                }

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root._isRequisitionsView
                        ? (root.selectedRequisitionModel.title || "Requisition Detail")
                        : (root.selectedPurchaseOrderModel.title || "Purchase Order Detail")
                    subtitle: root._isRequisitionsView
                        ? (root.selectedRequisitionModel.statusLabel || root.selectedRequisitionModel.subtitle || "")
                        : (root.selectedPurchaseOrderModel.statusLabel || root.selectedPurchaseOrderModel.subtitle || "")
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions

                    onBackRequested: { root._detailOpen = false }
                    onActionTriggered: function(actionId) {
                        if (root._isRequisitionsView) {
                            const state = root.selectedRequisitionModel.state || {}
                            if (actionId === "edit") {
                                dialogHostLoader.invoke("openEditRequisitionDialog", root.selectedRequisitionModel)
                            } else if (actionId === "submit" && state.requisitionId) {
                                root.workspaceController.submitRequisition(String(state.requisitionId || ""))
                            } else if (actionId === "cancel" && state.requisitionId) {
                                root.workspaceController.cancelRequisition(String(state.requisitionId || ""))
                            }
                        } else {
                            const state = root.selectedPurchaseOrderModel.state || {}
                            if (actionId === "edit") {
                                dialogHostLoader.invoke("openEditPurchaseOrderDialog", root.selectedPurchaseOrderModel)
                            } else if (actionId === "submit" && state.purchaseOrderId) {
                                root.workspaceController.submitPurchaseOrder(String(state.purchaseOrderId || ""))
                            } else if (actionId === "send" && state.purchaseOrderId) {
                                root.workspaceController.sendPurchaseOrder(String(state.purchaseOrderId || ""))
                            } else if (actionId === "receipt") {
                                const lines = root.workspaceController ? (root.workspaceController.purchaseOrderLines || {}) : {}
                                dialogHostLoader.invoke("openReceiptPostDialog", root.selectedPurchaseOrderModel, lines.items || [])
                            } else if (actionId === "close" && state.purchaseOrderId) {
                                root.workspaceController.closePurchaseOrder(String(state.purchaseOrderId || ""))
                            } else if (actionId === "cancel" && state.purchaseOrderId) {
                                root.workspaceController.cancelPurchaseOrder(String(state.purchaseOrderId || ""))
                            }
                        }
                    }
                }

                // ── Detail content ─────────────────────────────────
                Item {
                    id: _procDetailContent
                    width: parent ? parent.width : 0
                    implicitHeight: _procDetailArea.implicitHeight + 2 * Theme.AppTheme.pagePadding

                    readonly property int _idx: root._detailPage ? root._detailPage.activeSectionIndex : 0
                    readonly property var _detail: root._isRequisitionsView
                        ? root.selectedRequisitionModel : root.selectedPurchaseOrderModel
                    readonly property var _fields: _procDetailContent._detail
                        ? (_procDetailContent._detail.fields || []) : []
                    readonly property var _lines: root._isRequisitionsView
                        ? (root.workspaceController ? (root.workspaceController.requisitionLines || {}) : {})
                        : (root.workspaceController ? (root.workspaceController.purchaseOrderLines || {}) : {})
                    readonly property var _receipts: root._isRequisitionsView ? null
                        : (root.workspaceController ? (root.workspaceController.receipts || {}) : {})

                    // Section offsets: reqs: 0=Overview,1=Lines,2=Activity / POs: 0=Overview,1=Lines,2=Receipts,3=Activity
                    readonly property int _activityIdx: root._isRequisitionsView ? 2 : 3
                    readonly property int _receiptsIdx: 2
                    readonly property int _linesIdx: 1

                    Item {
                        id: _procDetailArea
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.pagePadding
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.AppTheme.pagePadding
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.AppTheme.pagePadding
                        implicitHeight: _procOverview.visible ? _procOverview.implicitHeight
                            : _procLines.visible ? _procLines.implicitHeight
                            : _procReceipts.visible ? _procReceipts.implicitHeight
                            : _procActivity.implicitHeight + Theme.AppTheme.spacingMd

                        // Overview
                        Item {
                            id: _procOverview
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            visible: _procDetailContent._idx === 0
                            implicitHeight: _procFieldsGrid.visible ? _procFieldsGrid.implicitHeight : _procEmpty.implicitHeight

                            GridLayout {
                                id: _procFieldsGrid
                                width: parent.width
                                columns: 2
                                columnSpacing: Theme.AppTheme.spacingMd
                                rowSpacing: Theme.AppTheme.spacingMd
                                visible: _procDetailContent._fields.length > 0

                                Repeater {
                                    model: _procDetailContent._fields

                                    delegate: ColumnLayout {
                                        id: _pfd
                                        required property var modelData
                                        Layout.fillWidth: true
                                        spacing: 2

                                        AppControls.Label {
                                            text: _pfd.modelData.label || ""
                                            color: Theme.AppTheme.textMuted
                                            font.pixelSize: Theme.AppTheme.captionSize
                                            font.family: Theme.AppTheme.fontFamily
                                            font.bold: true
                                        }
                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: _pfd.modelData.value || "—"
                                            color: Theme.AppTheme.textPrimary
                                            font.pixelSize: Theme.AppTheme.bodySize
                                            font.family: Theme.AppTheme.fontFamily
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }
                                    }
                                }
                            }

                            AppWidgets.EmptyState {
                                id: _procEmpty
                                width: parent.width
                                visible: _procDetailContent._fields.length === 0
                                title: _procDetailContent._detail
                                    ? (_procDetailContent._detail.emptyState || "No details available.")
                                    : "No details available."
                            }
                        }

                        // Lines (Requisition or PO lines)
                        Item {
                            id: _procLines
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            visible: _procDetailContent._idx === _procDetailContent._linesIdx
                            implicitHeight: _linesTable.implicitHeight + 80

                            AppWidgets.DataTable {
                                id: _linesTable
                                width: parent.width
                                height: Math.max(200, Math.min(480, implicitHeight))
                                multiSelect: false
                                columns: [
                                    { "key": "title",    "label": "Item",     "flex": 2 },
                                    { "key": "subtitle", "label": "Details",  "flex": 1.5 },
                                    { "key": "metaText", "label": "Quantity", "flex": 1 }
                                ]
                                rows: _procDetailContent._lines ? (_procDetailContent._lines.items || []) : []
                                loading: false
                                emptyText: _procDetailContent._lines
                                    ? (_procDetailContent._lines.emptyState || "No lines.")
                                    : "No lines."
                            }

                            AppControls.SecondaryButton {
                                anchors.top: _linesTable.bottom
                                anchors.topMargin: Theme.AppTheme.spacingSm
                                text: root._isRequisitionsView ? "Add Line" : "Add Line"
                                iconName: "add"
                                enabled: !root.workspaceController.isBusy
                                onClicked: {
                                    if (root._isRequisitionsView) {
                                        dialogHostLoader.invoke("openRequisitionLineDialog", root.selectedRequisitionModel)
                                    } else {
                                        dialogHostLoader.invoke("openPurchaseOrderLineDialog", root.selectedPurchaseOrderModel)
                                    }
                                }
                            }
                        }

                        // Receipts (PO only, index 2)
                        Item {
                            id: _procReceipts
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            visible: !root._isRequisitionsView && _procDetailContent._idx === _procDetailContent._receiptsIdx
                            implicitHeight: _receiptsTable.implicitHeight

                            AppWidgets.DataTable {
                                id: _receiptsTable
                                width: parent.width
                                height: Math.max(200, Math.min(480, implicitHeight))
                                multiSelect: false
                                columns: [
                                    { "key": "title",       "label": "Receipt",  "flex": 2 },
                                    { "key": "subtitle",    "label": "Details",  "flex": 1.5 },
                                    { "key": "statusLabel", "label": "Status",   "flex": 0, "minWidth": 90, "type": "status" },
                                    { "key": "metaText",    "label": "Date",     "flex": 1 }
                                ]
                                rows: _procDetailContent._receipts
                                    ? (_procDetailContent._receipts.items || []) : []
                                loading: false
                                emptyText: _procDetailContent._receipts
                                    ? (_procDetailContent._receipts.emptyState || "No receipts.")
                                    : "No receipts."
                            }
                        }

                        // Activity
                        AppWidgets.ActivityFeed {
                            id: _procActivity
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            visible: _procDetailContent._idx === _procDetailContent._activityIdx
                            items: []
                            emptyText: "Activity history will appear here."
                        }
                    }
                }
            }
        }
    }
}
