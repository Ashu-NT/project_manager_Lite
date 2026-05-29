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
    readonly property string _selectedStockId: root.workspaceController
        ? root.workspaceController.selectedStockSignalId : ""
    readonly property string _selectedSupplierId: root.workspaceController
        ? root.workspaceController.selectedSupplierPricingId : ""

    readonly property var selectedStockSignalModel: {
        const id = root._selectedStockId
        if (!id) return { "id": "", "title": "", "statusLabel": "", "subtitle": "", "fields": [], "emptyState": "Select a row to view details.", "state": {} }
        const items = root.stockSignalsModel.items || []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id || "") === id) {
                const r = items[i]
                const fields = []
                if (r.subtitle)       fields.push({ "label": "Storeroom",    "value": r.subtitle })
                if (r.statusLabel)    fields.push({ "label": "Signal",       "value": r.statusLabel })
                if (r.metaText)       fields.push({ "label": "On Hand",      "value": r.metaText })
                if (r.supportingText) fields.push({ "label": "Details",      "value": r.supportingText })
                return { "id": id, "title": r.title || "", "statusLabel": r.statusLabel || "", "subtitle": r.subtitle || "", "fields": fields, "emptyState": "", "state": r.state || {} }
            }
        }
        return { "id": id, "title": "", "statusLabel": "", "subtitle": "", "fields": [], "emptyState": "Details not available.", "state": {} }
    }

    readonly property var selectedSupplierPricingModel: {
        const id = root._selectedSupplierId
        if (!id) return { "id": "", "title": "", "statusLabel": "", "subtitle": "", "fields": [], "emptyState": "Select a row to view details.", "state": {} }
        const items = root.supplierPricingModel.items || []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id || "") === id) {
                const r = items[i]
                const fields = []
                if (r.subtitle)       fields.push({ "label": "Supplier",    "value": r.subtitle })
                if (r.statusLabel)    fields.push({ "label": "Type",        "value": r.statusLabel })
                if (r.metaText)       fields.push({ "label": "Unit Price",  "value": r.metaText })
                if (r.supportingText) fields.push({ "label": "Details",     "value": r.supportingText })
                return { "id": id, "title": r.title || "", "statusLabel": r.statusLabel || "", "subtitle": r.subtitle || "", "fields": fields, "emptyState": "", "state": r.state || {} }
            }
        }
        return { "id": id, "title": "", "statusLabel": "", "subtitle": "", "fields": [], "emptyState": "Details not available.", "state": {} }
    }

    readonly property bool _isStockView: root.workspaceController
        ? root.workspaceController.activeView === "stock"
        : true

    title: root.overviewModel.title || "Pricing & Valuation"
    subtitle: root.overviewModel.subtitle || ""

    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    property string _pendingExportAction: ""
    readonly property var _detailPage: _detailPageLoader.item

    readonly property var _stockColumns: [
        { "key": "title",       "label": "Item",         "flex": 2,   "sortable": true },
        { "key": "subtitle",    "label": "Storeroom",    "flex": 1.5 },
        { "key": "statusLabel", "label": "Signal",       "flex": 0,   "minWidth": 90, "type": "status" },
        { "key": "metaText",    "label": "On Hand / Min","flex": 1 }
    ]
    readonly property var _supplierColumns: [
        { "key": "title",       "label": "Item",         "flex": 2,   "sortable": true },
        { "key": "subtitle",    "label": "Supplier",     "flex": 1.5 },
        { "key": "statusLabel", "label": "Type",         "flex": 0,   "minWidth": 90, "type": "status" },
        { "key": "metaText",    "label": "Unit Price",   "flex": 1 }
    ]

    readonly property var _detailSections: ["Overview", "Activity"]

    function _optionIndexForValue(options, value) {
        const optList = options || []
        for (let i = 0; i < optList.length; i++) {
            if (String(optList[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    function _loadLazyDetailSection(sectionIndex) {
        if (root.workspaceController === null) return
        if (sectionIndex !== 1) return
        const entityId = root._isStockView
            ? String(root._selectedStockId || "")
            : String(root._selectedSupplierId || "")
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
        const stamp = String(now.getFullYear())
            + String(now.getMonth() + 1).padStart(2, "0")
            + String(now.getDate()).padStart(2, "0")
            + "_"
            + String(now.getHours()).padStart(2, "0")
            + String(now.getMinutes()).padStart(2, "0")
            + String(now.getSeconds()).padStart(2, "0")
        switch (actionName) {
        case "stockCsv":    return "inventory-stock-status_" + stamp + ".csv"
        case "stockExcel":  return "inventory-stock-status_" + stamp + ".xlsx"
        case "procCsv":     return "inventory-procurement-overview_" + stamp + ".csv"
        case "procExcel":   return "inventory-procurement-overview_" + stamp + ".xlsx"
        default:            return "inventory-report_" + stamp + ".csv"
        }
    }

    function _triggerExport(selectedFile) {
        if (root.workspaceController === null) return
        switch (root._pendingExportAction) {
        case "stockCsv":   root.workspaceController.exportStockStatusCsv(String(selectedFile || "")); break
        case "stockExcel": root.workspaceController.exportStockStatusExcel(String(selectedFile || "")); break
        case "procCsv":    root.workspaceController.exportProcurementOverviewCsv(String(selectedFile || "")); break
        case "procExcel":  root.workspaceController.exportProcurementOverviewExcel(String(selectedFile || "")); break
        }
    }

    // ── Export dialog ──────────────────────────────────────────────
    FileDialog {
        id: exportDialog
        title: root._pendingExportAction.indexOf("Excel") >= 0 ? "Export Excel" : "Export CSV"
        fileMode: FileDialog.SaveFile
        nameFilters: root._pendingExportAction.indexOf("Excel") >= 0
            ? ["Excel files (*.xlsx)"] : ["CSV files (*.csv)"]
        currentFile: root._exportDefaultTarget(root._pendingExportAction)
        onAccepted: root._triggerExport(selectedFile)
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
                    message: "Loading pricing data..."
                }
                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root.workspaceController
                        ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    tone: "info"
                    message: "Processing..."
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
                    searchText: ""
                    searchPlaceholder: root._isStockView ? "Search stock signals..." : "Search supplier pricing..."
                    showFilter: true
                    showViews: true
                    showRefresh: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onFilterClicked: filterPopup.open()
                    onViewsClicked: viewsPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onExportRequested: exportActionsPopup.open()
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: _stockTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: _paginationBar.top
                        visible: root._isStockView
                        multiSelect: false
                        columns: root._stockColumns
                        sourceModel: root.workspaceController ? root.workspaceController.stockSignalsTableModel : null
                        rows: root.stockSignalsModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.stockSignalsModel.emptyState || "No stock signals."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedStockSignalId : ""

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectStockSignal(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectStockSignal(rowId)
                            root._openDetail(0)
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.DataTable {
                        id: _supplierTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: _paginationBar.top
                        visible: !root._isStockView
                        multiSelect: false
                        columns: root._supplierColumns
                        sourceModel: root.workspaceController ? root.workspaceController.supplierPricingTableModel : null
                        rows: root.supplierPricingModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.supplierPricingModel.emptyState || "No supplier pricing records."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedSupplierPricingId : ""

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectSupplierPricing(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectSupplierPricing(rowId)
                            root._openDetail(0)
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        currentPage: root._isStockView
                            ? (root.workspaceController ? root.workspaceController.stockSignalPage : 1)
                            : (root.workspaceController ? root.workspaceController.supplierPricingPage : 1)
                        pageSize: root._isStockView
                            ? (root.workspaceController ? root.workspaceController.stockSignalPageSize : 25)
                            : (root.workspaceController ? root.workspaceController.supplierPricingPageSize : 25)
                        totalItems: root._isStockView
                            ? (root.workspaceController ? root.workspaceController.stockSignalTotalCount : 0)
                            : (root.workspaceController ? root.workspaceController.supplierPricingTotalCount : 0)
                        busy: root.workspaceController ? root.workspaceController.isBusy : false

                        onPageRequested: function(page) {
                            if (root.workspaceController === null) return
                            if (root._isStockView) root.workspaceController.setStockSignalPage(page)
                            else root.workspaceController.setSupplierPricingPage(page)
                        }
                        onPageSizeRequested: function(size) {
                            if (root.workspaceController === null) return
                            if (root._isStockView) root.workspaceController.setStockSignalPageSize(size)
                            else root.workspaceController.setSupplierPricingPageSize(size)
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
                                text: "Storeroom"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                                visible: root._isStockView
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                visible: root._isStockView
                                model: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.storeroomOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setStoreroomFilter(String(opts[index].value || "all"))
                                    }
                                }
                            }

                            AppControls.Label {
                                text: "Supplier"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                                visible: !root._isStockView
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                visible: !root._isStockView
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
                                text: "Limit"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                                visible: root._isStockView
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                visible: root._isStockView
                                model: root.workspaceController ? (root.workspaceController.limitOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.limitOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedLimitFilter : "200"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.limitOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setLimitFilter(String(opts[index].value || "200"))
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
                                text: "Stock Status"
                                iconName: "inventory"
                                enabled: !root._isStockView
                                onClicked: {
                                    if (root.workspaceController !== null) root.workspaceController.setActiveView("stock")
                                    viewsPopup.close()
                                }
                            }
                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text: "Supplier Pricing"
                                iconName: "procurement"
                                enabled: root._isStockView
                                onClicked: {
                                    if (root.workspaceController !== null) root.workspaceController.setActiveView("supplier_pricing")
                                    viewsPopup.close()
                                }
                            }
                        }
                    }

                    // ── Export actions popup ───────────────────────
                    AppWidgets.AnchoredPopup {
                        id: exportActionsPopup
                        anchorItem: tableToolbar
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
                                text: "Export"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text: "Stock Status CSV"
                                iconName: "export"
                                enabled: root.workspaceController ? root.workspaceController.canExport : false
                                onClicked: {
                                    root._pendingExportAction = "stockCsv"
                                    exportActionsPopup.close()
                                    exportDialog.open()
                                }
                            }
                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text: "Stock Status Excel"
                                iconName: "export"
                                enabled: root.workspaceController ? root.workspaceController.canExport : false
                                onClicked: {
                                    root._pendingExportAction = "stockExcel"
                                    exportActionsPopup.close()
                                    exportDialog.open()
                                }
                            }
                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text: "Procurement CSV"
                                iconName: "export"
                                enabled: root.workspaceController ? root.workspaceController.canExport : false
                                onClicked: {
                                    root._pendingExportAction = "procCsv"
                                    exportActionsPopup.close()
                                    exportDialog.open()
                                }
                            }
                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text: "Procurement Excel"
                                iconName: "export"
                                enabled: root.workspaceController ? root.workspaceController.canExport : false
                                onClicked: {
                                    root._pendingExportAction = "procExcel"
                                    exportActionsPopup.close()
                                    exportDialog.open()
                                }
                            }
                        }
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
                onSectionChanged: function(index) { root._loadLazyDetailSection(index) }

                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                    root._loadLazyDetailSection(root._pendingDetailSection)
                }

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root._isStockView
                        ? (root.selectedStockSignalModel.title || "Stock Signal")
                        : (root.selectedSupplierPricingModel.title || "Supplier Pricing")
                    subtitle: root._isStockView
                        ? (root.selectedStockSignalModel.statusLabel || root.selectedStockSignalModel.subtitle || "")
                        : (root.selectedSupplierPricingModel.statusLabel || root.selectedSupplierPricingModel.subtitle || "")
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: []

                    onBackRequested: { root._detailOpen = false }
                }

                Item {
                    id: _pricingDetailContent
                    width: parent ? parent.width : 0
                    implicitHeight: _pricingDetailArea.implicitHeight + 2 * Theme.AppTheme.pagePadding

                    readonly property int _idx: root._detailPage ? root._detailPage.activeSectionIndex : 0
                    readonly property var _detail: root._isStockView
                        ? root.selectedStockSignalModel : root.selectedSupplierPricingModel
                    readonly property var _fields: _pricingDetailContent._detail
                        ? (_pricingDetailContent._detail.fields || []) : []

                    Item {
                        id: _pricingDetailArea
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.pagePadding
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.AppTheme.pagePadding
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.AppTheme.pagePadding
                        implicitHeight: _pricingOverview.visible ? _pricingOverview.implicitHeight
                            : _pricingActivity.implicitHeight + Theme.AppTheme.spacingMd

                        Item {
                            id: _pricingOverview
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            visible: _pricingDetailContent._idx === 0
                            implicitHeight: _pricingFieldsGrid.visible ? _pricingFieldsGrid.implicitHeight : _pricingEmpty.implicitHeight

                            GridLayout {
                                id: _pricingFieldsGrid
                                width: parent.width
                                columns: 2
                                columnSpacing: Theme.AppTheme.spacingMd
                                rowSpacing: Theme.AppTheme.spacingMd
                                visible: _pricingDetailContent._fields.length > 0

                                Repeater {
                                    model: _pricingDetailContent._fields

                                    delegate: ColumnLayout {
                                        id: _prfd
                                        required property var modelData
                                        Layout.fillWidth: true
                                        spacing: 2

                                        AppControls.Label {
                                            text: _prfd.modelData.label || ""
                                            color: Theme.AppTheme.textMuted
                                            font.pixelSize: Theme.AppTheme.captionSize
                                            font.family: Theme.AppTheme.fontFamily
                                            font.bold: true
                                        }
                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: _prfd.modelData.value || "—"
                                            color: Theme.AppTheme.textPrimary
                                            font.pixelSize: Theme.AppTheme.bodySize
                                            font.family: Theme.AppTheme.fontFamily
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }
                                    }
                                }
                            }

                            AppWidgets.EmptyState {
                                id: _pricingEmpty
                                width: parent.width
                                visible: _pricingDetailContent._fields.length === 0
                                title: _pricingDetailContent._detail
                                    ? (_pricingDetailContent._detail.emptyState || "No details available.")
                                    : "No details available."
                            }
                        }

                        AppWidgets.ActivityFeed {
                            id: _pricingActivity
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            visible: _pricingDetailContent._idx === 1
                            items: root.workspaceController ? (root.workspaceController.detailActivityItems || []) : []
                            emptyText: "No activity recorded yet."
                        }
                    }
                }
            }
        }
    }
}
