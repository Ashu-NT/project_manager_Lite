pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import "panels" as Panels
import "components" as Components

AppLayouts.WorkspaceFrame {
    id: root

    property var platformCatalog
    property var _caps: ({})

    Component.onCompleted: {
        if (root.platformCatalog) root._caps = root.platformCatalog.capabilitySnapshot()
    }

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementPricingWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.pricingWorkspace
        : null

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": "Pricing & Valuation", "subtitle": "Supplier pricing analysis and stock status reporting.", "metrics": [] })
    readonly property var stockSignalsModel: root.workspaceController
        ? root.workspaceController.stockSignals
        : ({ "items": [], "emptyState": "No stock signals available." })
    readonly property var supplierPricingModel: root.workspaceController
        ? root.workspaceController.supplierPricing
        : ({ "items": [], "emptyState": "No supplier pricing records." })

    readonly property bool _isStockView: root.workspaceController
        ? root.workspaceController.activeView === "stock"
        : true

    // ── Derived detail models (computed from selected row) ─────────────
    readonly property var _selectedStockId: root.workspaceController ? root.workspaceController.selectedStockSignalId : ""
    readonly property var _selectedSupplierId: root.workspaceController ? root.workspaceController.selectedSupplierPricingId : ""

    readonly property var selectedStockSignalModel: {
        const id = root._selectedStockId
        if (!id) return { "id": "", "fields": [], "emptyState": "Select a row to view details.", "state": {} }
        const items = root.stockSignalsModel.items || []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id || "") === id) {
                const r = items[i]
                return { "id": id, "title": r.title || "", "statusLabel": r.statusLabel || "", "subtitle": r.subtitle || "",
                    "fields": [
                        r.subtitle       ? { "label": "Storeroom", "value": r.subtitle }       : null,
                        r.statusLabel    ? { "label": "Signal",    "value": r.statusLabel }    : null,
                        r.metaText       ? { "label": "On Hand",   "value": r.metaText }       : null,
                        r.supportingText ? { "label": "Details",   "value": r.supportingText } : null
                    ].filter(Boolean), "emptyState": "", "state": r.state || {} }
            }
        }
        return { "id": id, "title": "", "statusLabel": "", "subtitle": "", "fields": [], "emptyState": "Details not available.", "state": {} }
    }

    readonly property var selectedSupplierPricingModel: {
        const id = root._selectedSupplierId
        if (!id) return { "id": "", "fields": [], "emptyState": "Select a row to view details.", "state": {} }
        const items = root.supplierPricingModel.items || []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id || "") === id) {
                const r = items[i]
                return { "id": id, "title": r.title || "", "statusLabel": r.statusLabel || "", "subtitle": r.subtitle || "",
                    "fields": [
                        r.subtitle       ? { "label": "Supplier",   "value": r.subtitle }       : null,
                        r.statusLabel    ? { "label": "Type",       "value": r.statusLabel }    : null,
                        r.metaText       ? { "label": "Unit Price", "value": r.metaText }       : null,
                        r.supportingText ? { "label": "Details",    "value": r.supportingText } : null
                    ].filter(Boolean), "emptyState": "", "state": r.state || {} }
            }
        }
        return { "id": id, "title": "", "statusLabel": "", "subtitle": "", "fields": [], "emptyState": "Details not available.", "state": {} }
    }

    title:    root.overviewModel.title    || "Pricing & Valuation"
    subtitle: root.overviewModel.subtitle || ""

    // ── Detail state ───────────────────────────────────────────────────
    property bool _detailOpen: false
    property int  _pendingDetailSection: 0
    property string _pendingExportAction: ""
    readonly property var _detailPage: _detailPageLoader.item

    function _loadLazyDetailSection(sectionIndex) {
        if (root.workspaceController === null || sectionIndex !== 1) return
        const entityId   = root._isStockView ? String(root._selectedStockId || "") : String(root._selectedSupplierId || "")
        const entityType = root._isStockView ? "inventory_item" : "purchase_order"
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

    function _exportDefaultTarget(actionName) {
        const now = new Date()
        const stamp = String(now.getFullYear()) + String(now.getMonth() + 1).padStart(2, "0") + String(now.getDate()).padStart(2, "0") + "_" + String(now.getHours()).padStart(2, "0") + String(now.getMinutes()).padStart(2, "0") + String(now.getSeconds()).padStart(2, "0")
        switch (actionName) {
        case "stockCsv":   return "inventory-stock-status_"          + stamp + ".csv"
        case "stockExcel": return "inventory-stock-status_"          + stamp + ".xlsx"
        case "procCsv":    return "inventory-procurement-overview_"  + stamp + ".csv"
        case "procExcel":  return "inventory-procurement-overview_"  + stamp + ".xlsx"
        default:           return "inventory-report_"                + stamp + ".csv"
        }
    }

    function _triggerExport(selectedFile) {
        if (root.workspaceController === null) return
        switch (root._pendingExportAction) {
        case "stockCsv":   root.workspaceController.exportStockStatusCsv(String(selectedFile || ""));           break
        case "stockExcel": root.workspaceController.exportStockStatusExcel(String(selectedFile || ""));         break
        case "procCsv":    root.workspaceController.exportProcurementOverviewCsv(String(selectedFile || ""));   break
        case "procExcel":  root.workspaceController.exportProcurementOverviewExcel(String(selectedFile || "")); break
        }
    }

    FileDialog {
        id: exportDialog
        title:       root._pendingExportAction.indexOf("Excel") >= 0 ? "Export Excel" : "Export CSV"
        fileMode:    FileDialog.SaveFile
        nameFilters: root._pendingExportAction.indexOf("Excel") >= 0 ? ["Excel files (*.xlsx)"] : ["CSV files (*.csv)"]
        currentFile: root._exportDefaultTarget(root._pendingExportAction)
        onAccepted:  root._triggerExport(selectedFile)
    }

    // ── Stacked list / detail ──────────────────────────────────────────
    Item {
        anchors.fill: parent

        Item {
            anchors.fill: parent
            visible: !root._detailOpen || _detailPageLoader.status !== Loader.Ready

            Components.PricingListPage {
                anchors.fill:          parent
                workspaceController:   root.workspaceController
                overviewModel:         root.overviewModel
                stockSignalsModel:     root.stockSignalsModel
                supplierPricingModel:  root.supplierPricingModel
                detailOpen:            root._detailOpen

                onRowActivated:         root._openDetail(0)
                onExportActionRequested: function(actionName) {
                    root._pendingExportAction = actionName
                    exportDialog.open()
                }
            }
        }

        Loader {
            id: _detailPageLoader
            anchors.fill: parent
            active:       root._detailOpen
            visible:      root._detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent

            AppWidgets.SectionDetailPage {
                open:        true
                anchors.fill: parent
                showHeader:  false
                showEdit:    false
                showDelete:  false
                isBusy:      root.workspaceController ? root.workspaceController.isBusy : false
                sections:    ["Overview", "Activity"]
                z:           20
                onSectionChanged: function(index) { root._loadLazyDetailSection(index) }
                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                    root._loadLazyDetailSection(root._pendingDetailSection)
                }

                AppWidgets.ContextualActionToolbar {
                    detailPagePinned: true
                    width:    parent ? parent.width : 0
                    showBack: true
                    title:    root._isStockView ? (root.selectedStockSignalModel.title || "Stock Signal") : (root.selectedSupplierPricingModel.title || "Supplier Pricing")
                    subtitle: root._isStockView ? (root.selectedStockSignalModel.statusLabel || root.selectedStockSignalModel.subtitle || "") : (root.selectedSupplierPricingModel.statusLabel || root.selectedSupplierPricingModel.subtitle || "")
                    busy:     root.workspaceController ? root.workspaceController.isBusy : false
                    actions:  []
                    onBackRequested: { root._detailOpen = false }
                }

                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0; tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : "" }
                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0 && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : "" }

                Panels.PricingDetailPanel {
                    width:                 parent ? parent.width : 0
                    detailPage:            root._detailPage
                    isStockView:           root._isStockView
                    stockSignalDetail:     root.selectedStockSignalModel
                    supplierPricingDetail: root.selectedSupplierPricingModel
                    activityItems:         root.workspaceController ? (root.workspaceController.detailActivityItems || []) : []
                }
            }
        }
    }
}
