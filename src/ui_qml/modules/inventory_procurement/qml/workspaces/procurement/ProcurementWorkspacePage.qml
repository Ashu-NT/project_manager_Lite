pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import "dialogs" as Dialogs
import "sections" as Sections
import "components" as Components
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import QtQuick.Dialogs

AppLayouts.WorkspaceFrame {
    id: root

    property var platformCatalog
    property var _caps: ({})

    FileDialog {
        id: _exportDialog
        title: "Export Procurement"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Excel files (*.xlsx)", "CSV files (*.csv)"]
        onAccepted: {
            if (root.workspaceController !== null) {
                const columns = root._isRequisitionsView ? root._requisitionColumns : root._purchaseOrderColumns
                const cols = columns.filter(function(c) { return c.visible !== false })
                    .map(function(c) { return { "key": c.key, "label": c.label } })
                root.workspaceController.exportTable(cols, String(selectedFile || ""))
            }
        }
    }

    Component.onCompleted: {
        if (root.platformCatalog) root._caps = root.platformCatalog.capabilitySnapshot()
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
        { "key": "requestingSiteLabel", "label": "Site", "flex": 1.2, "sortable": true },
        { "key": "requestingStoreroomLabel", "label": "Storeroom", "flex": 1.4, "sortable": true },
        { "key": "statusLabel", "label": "Status",       "flex": 0,   "minWidth": 90, "type": "status" },
        { "key": "supportingText", "label": "Priority / Need", "flex": 1.5 }
    ]
    readonly property var _purchaseOrderColumns: [
        { "key": "title",       "label": "Purchase Order", "flex": 2,  "sortable": true },
        { "key": "siteLabel",   "label": "Site",           "flex": 1.2, "sortable": true },
        { "key": "supplierLabel", "label": "Supplier",     "flex": 1.5, "sortable": true },
        { "key": "statusLabel", "label": "Status",         "flex": 0,  "minWidth": 90, "type": "status" },
        { "key": "supportingText", "label": "Currency / Delivery", "flex": 1.5 }
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

    function _loadLazyDetailSection(sectionIndex) {
        if (root.workspaceController === null) return
        const activityIdx = root._isRequisitionsView ? 2 : 3
        if (sectionIndex !== activityIdx) return
        const entityId = root._isRequisitionsView
            ? String(root.selectedRequisitionModel.id || "")
            : String(root.selectedPurchaseOrderModel.id || "")
        const entityType = root._isRequisitionsView ? "purchase_requisition" : "purchase_order"
        root.workspaceController.loadDetailActivity(entityId, entityType)
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (root._detailPage) {
            root._detailPage.scrollToSection(sectionIndex)
            root._loadLazyDetailSection(sectionIndex)
        }
    }

    // ── Dialog host ───────────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.ProcurementDialogHost {
                siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                supplierOptions: root.workspaceController ? (root.workspaceController.supplierOptions || []) : []
                itemOptions: root.workspaceController ? (root.workspaceController.itemOptions || []) : []
                requisitionOptions: root.workspaceController ? (root.workspaceController.requisitionOptions || []) : []
                requisitionLineOptions: root.workspaceController ? (root.workspaceController.requisitionLineOptions || []) : []
                workspaceController: root.workspaceController
            }
        }
    }

    // ── Stacked list / detail ─────────────────────────────────────────────
    Item {
        anchors.fill: parent

        Item {
            anchors.fill: parent
            visible: !root._detailOpen || _detailPageLoader.status !== Loader.Ready

            Components.ProcurementListPage {
                anchors.fill: parent
                workspaceController: root.workspaceController
                overviewModel: root.overviewModel
                requisitionsModel: root.requisitionsModel
                purchaseOrdersModel: root.purchaseOrdersModel
                requisitionColumns: root._requisitionColumns
                purchaseOrderColumns: root._purchaseOrderColumns
                onRowActivated: function(isRequisition, rowId) { root._openDetail(0) }
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
                onExportRequested: _exportDialog.open()
            }
        }

        // ── Detail page (lazy loaded) ─────────────────────────────────────
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
                showHeader: false; showEdit: false; showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: root._detailSections
                z: 20
                onSectionChanged: function(index) { root._loadLazyDetailSection(index) }
                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                    root._loadLazyDetailSection(root._pendingDetailSection)
                }

                AppWidgets.ContextualActionToolbar {
                    detailPagePinned: true
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
                            if (actionId === "edit") dialogHostLoader.invoke("openEditRequisitionDialog", root.selectedRequisitionModel)
                            else if (actionId === "submit" && state.requisitionId) root.workspaceController.submitRequisition(String(state.requisitionId || ""))
                            else if (actionId === "cancel" && state.requisitionId) root.workspaceController.cancelRequisition(String(state.requisitionId || ""))
                        } else {
                            const state = root.selectedPurchaseOrderModel.state || {}
                            if (actionId === "edit") dialogHostLoader.invoke("openEditPurchaseOrderDialog", root.selectedPurchaseOrderModel)
                            else if (actionId === "submit" && state.purchaseOrderId) root.workspaceController.submitPurchaseOrder(String(state.purchaseOrderId || ""))
                            else if (actionId === "send" && state.purchaseOrderId) root.workspaceController.sendPurchaseOrder(String(state.purchaseOrderId || ""))
                            else if (actionId === "receipt") {
                                const lines = root.workspaceController ? (root.workspaceController.purchaseOrderLines || {}) : {}
                                dialogHostLoader.invoke("openReceiptPostDialog", root.selectedPurchaseOrderModel, lines.items || [])
                            }
                            else if (actionId === "close" && state.purchaseOrderId) root.workspaceController.closePurchaseOrder(String(state.purchaseOrderId || ""))
                            else if (actionId === "cancel" && state.purchaseOrderId) root.workspaceController.cancelPurchaseOrder(String(state.purchaseOrderId || ""))
                        }
                    }
                }

                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: root._detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Item {
                    id: _procDetailContent
                    width: parent ? parent.width : 0
                    implicitHeight: _procDetailArea.implicitHeight + 2 * Theme.AppTheme.pagePadding

                    readonly property int _idx: root._detailPage ? root._detailPage.activeSectionIndex : 0
                    readonly property var _detail: root._isRequisitionsView ? root.selectedRequisitionModel : root.selectedPurchaseOrderModel
                    readonly property var _fields: _procDetailContent._detail ? (_procDetailContent._detail.fields || []) : []
                    readonly property var _lines: root._isRequisitionsView
                        ? (root.workspaceController ? (root.workspaceController.requisitionLines || {}) : {})
                        : (root.workspaceController ? (root.workspaceController.purchaseOrderLines || {}) : {})
                    readonly property var _receipts: root._isRequisitionsView ? null : (root.workspaceController ? (root.workspaceController.receipts || {}) : {})
                    readonly property int _activityIdx: root._isRequisitionsView ? 2 : 3
                    readonly property int _receiptsIdx: 2
                    readonly property int _linesIdx: 1

                    Item {
                        id: _procDetailArea
                        anchors.top: parent.top; anchors.topMargin: Theme.AppTheme.pagePadding
                        anchors.left: parent.left; anchors.leftMargin: Theme.AppTheme.pagePadding
                        anchors.right: parent.right; anchors.rightMargin: Theme.AppTheme.pagePadding
                        implicitHeight: _procOverview.visible ? _procOverview.implicitHeight
                            : _procLines.visible ? _procLines.implicitHeight
                            : _procReceipts.visible ? _procReceipts.implicitHeight
                            : _procActivity.implicitHeight + Theme.AppTheme.spacingMd

                        Item {
                            id: _procOverview
                            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                            visible: _procDetailContent._idx === 0
                            implicitHeight: _procFieldsGrid.visible ? _procFieldsGrid.implicitHeight : _procEmpty.implicitHeight

                            GridLayout {
                                id: _procFieldsGrid
                                width: parent.width; columns: 2
                                columnSpacing: Theme.AppTheme.spacingMd; rowSpacing: Theme.AppTheme.spacingMd
                                visible: _procDetailContent._fields.length > 0

                                Repeater {
                                    model: _procDetailContent._fields
                                    delegate: ColumnLayout {
                                        id: _pfd
                                        required property var modelData
                                        Layout.fillWidth: true; spacing: 2
                                        AppControls.Label { text: _pfd.modelData.label || ""; color: Theme.AppTheme.textMuted; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; font.bold: true }
                                        AppControls.Label { Layout.fillWidth: true; text: _pfd.modelData.value || "–"; color: Theme.AppTheme.textPrimary; font.pixelSize: Theme.AppTheme.bodySize; font.family: Theme.AppTheme.fontFamily; wrapMode: Text.WrapAtWordBoundaryOrAnywhere }
                                    }
                                }
                            }
                            AppWidgets.EmptyState {
                                id: _procEmpty; width: parent.width
                                visible: _procDetailContent._fields.length === 0
                                title: _procDetailContent._detail ? (_procDetailContent._detail.emptyState || "No details available.") : "No details available."
                            }
                        }

                        Item {
                            id: _procLines
                            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                            visible: _procDetailContent._idx === _procDetailContent._linesIdx
                            implicitHeight: _linesTable.implicitHeight + 80

                            AppWidgets.DataTable {
                                id: _linesTable; width: parent.width
                                height: Math.max(200, Math.min(480, implicitHeight)); multiSelect: false
                                columns: [
                                    { "key": "title",    "label": "Item",     "flex": 2 },
                                    { "key": "subtitle", "label": "Details",  "flex": 1.5 },
                                    { "key": "metaText", "label": "Quantity", "flex": 1 }
                                ]
                                sourceModel: root.workspaceController ? (root._isRequisitionsView ? root.workspaceController.requisitionLinesTableModel : root.workspaceController.purchaseOrderLinesTableModel) : null
                                loading: false
                                emptyText: _procDetailContent._lines ? (_procDetailContent._lines.emptyState || "No lines.") : "No lines."
                            }
                            AppControls.SecondaryButton {
                                anchors.top: _linesTable.bottom; anchors.topMargin: Theme.AppTheme.spacingSm
                                text: "Add Line"; iconName: "add"
                                enabled: !root.workspaceController.isBusy
                                onClicked: {
                                    if (root._isRequisitionsView) dialogHostLoader.invoke("openRequisitionLineDialog", root.selectedRequisitionModel)
                                    else dialogHostLoader.invoke("openPurchaseOrderLineDialog", root.selectedPurchaseOrderModel)
                                }
                            }
                        }

                        Item {
                            id: _procReceipts
                            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                            visible: !root._isRequisitionsView && _procDetailContent._idx === _procDetailContent._receiptsIdx
                            implicitHeight: _receiptsTable.implicitHeight

                            AppWidgets.DataTable {
                                id: _receiptsTable; width: parent.width
                                height: Math.max(200, Math.min(480, implicitHeight)); multiSelect: false
                                columns: [
                                    { "key": "title",       "label": "Receipt",  "flex": 2 },
                                    { "key": "subtitle",    "label": "Details",  "flex": 1.5 },
                                    { "key": "statusLabel", "label": "Status",   "flex": 0, "minWidth": 90, "type": "status" },
                                    { "key": "metaText",    "label": "Date",     "flex": 1 }
                                ]
                                sourceModel: root.workspaceController ? root.workspaceController.receiptsTableModel : null
                                loading: false
                                emptyText: _procDetailContent._receipts ? (_procDetailContent._receipts.emptyState || "No receipts.") : "No receipts."
                            }
                        }

                        AppWidgets.ActivityFeed {
                            id: _procActivity
                            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                            visible: _procDetailContent._idx === _procDetailContent._activityIdx
                            items: root.workspaceController ? (root.workspaceController.detailActivityItems || []) : []
                            emptyText: "No activity recorded yet."
                        }
                    }
                }
            }
        }
    }
}
