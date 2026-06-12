pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers

Item {
    id: root

    // ── Inputs ────────────────────────────────────────────────────────────
    property InventoryProcurementControllers.InventoryProcurementPricingWorkspaceController workspaceController
    property var overviewModel:        ({ "metrics": [] })
    property var stockSignalsModel:    ({ "emptyState": "No stock signals available.", "items": [] })
    property var supplierPricingModel: ({ "emptyState": "No supplier pricing records.", "items": [] })
    property bool detailOpen: false

    // ── Signals ───────────────────────────────────────────────────────────
    signal rowActivated()
    signal exportActionRequested(string actionName)

    // ── Derived ───────────────────────────────────────────────────────────
    readonly property bool _isStockView: root.workspaceController
        ? root.workspaceController.activeView === "stock"
        : true

    readonly property var _stockColumns: [
        { "key": "title",       "label": "Item",          "flex": 2,   "sortable": true },
        { "key": "subtitle",    "label": "Storeroom",     "flex": 1.5 },
        { "key": "statusLabel", "label": "Signal",        "flex": 0,   "minWidth": 90, "type": "status" },
        { "key": "metaText",    "label": "On Hand / Min", "flex": 1   }
    ]
    readonly property var _supplierColumns: [
        { "key": "title",       "label": "Item",       "flex": 2,   "sortable": true },
        { "key": "subtitle",    "label": "Supplier",   "flex": 1.5 },
        { "key": "statusLabel", "label": "Type",       "flex": 0,   "minWidth": 90, "type": "status" },
        { "key": "metaText",    "label": "Unit Price", "flex": 1   }
    ]

    function _optionIndexForValue(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    // ── Layout ────────────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.KpiStrip { Layout.fillWidth: true; metrics: root.overviewModel.metrics || [] }

        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: (root.workspaceController ? root.workspaceController.isLoading : false) && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            message: "Loading pricing data..."; compact: true; modal: false
        }
        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: root.workspaceController ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0 : false
            message: "Processing..."; compact: true; modal: false
        }
        AppWidgets.InlineMessage { Layout.fillWidth: true; visible: !root.detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0; tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : "" }
        AppWidgets.InlineMessage { Layout.fillWidth: true; visible: !root.detailOpen && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0 && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : "" }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchText:        ""
            searchPlaceholder: root._isStockView ? "Search stock signals..." : "Search supplier pricing..."
            showFilter:  true
            showViews:   true
            showRefresh: true
            showExport:  true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onFilterClicked:    filterPopup.open()
            onViewsClicked:     viewsPopup.open()
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
            onExportRequested:  exportActionsPopup.open()
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: _paginationBar.top
                visible:    root._isStockView
                multiSelect: false
                columns:    root._stockColumns
                sourceModel: root.workspaceController ? root.workspaceController.stockSignalsTableModel : null
                loading:     root.workspaceController ? root.workspaceController.isLoading : false
                emptyText:   root.stockSignalsModel.emptyState || "No stock signals."
                selectedRowId: root.workspaceController ? root.workspaceController.selectedStockSignalId : ""
                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectStockSignal(rowId) }
                onRowActivated: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectStockSignal(rowId); root.rowActivated() }
            }

            AppWidgets.DataTable {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: _paginationBar.top
                visible:    !root._isStockView
                multiSelect: false
                columns:    root._supplierColumns
                sourceModel: root.workspaceController ? root.workspaceController.supplierPricingTableModel : null
                loading:     root.workspaceController ? root.workspaceController.isLoading : false
                emptyText:   root.supplierPricingModel.emptyState || "No supplier pricing records."
                selectedRowId: root.workspaceController ? root.workspaceController.selectedSupplierPricingId : ""
                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectSupplierPricing(rowId) }
                onRowActivated: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectSupplierPricing(rowId); root.rowActivated() }
            }

            AppWidgets.TablePaginationBar {
                id: _paginationBar
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                currentPage: root._isStockView ? (root.workspaceController ? root.workspaceController.stockSignalPage : 1) : (root.workspaceController ? root.workspaceController.supplierPricingPage : 1)
                pageSize:    root._isStockView ? (root.workspaceController ? root.workspaceController.stockSignalPageSize : 25) : (root.workspaceController ? root.workspaceController.supplierPricingPageSize : 25)
                totalItems:  root._isStockView ? (root.workspaceController ? root.workspaceController.stockSignalTotalCount : 0) : (root.workspaceController ? root.workspaceController.supplierPricingTotalCount : 0)
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                onPageRequested: function(page) { if (root.workspaceController === null) return; if (root._isStockView) root.workspaceController.setStockSignalPage(page); else root.workspaceController.setSupplierPricingPage(page) }
                onPageSizeRequested: function(size) { if (root.workspaceController === null) return; if (root._isStockView) root.workspaceController.setStockSignalPageSize(size); else root.workspaceController.setSupplierPricingPageSize(size) }
            }

            // ── Filter popup ──────────────────────────────────────────
            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: tableToolbar.filterButtonItem; width: 304; padding: Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: Theme.AppTheme.radiusLg; color: Theme.AppTheme.surfaceRaised; border.color: Theme.AppTheme.divider; border.width: 1 }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label { text: "Site";     font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.siteOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.siteOptions || []) : [], root.workspaceController ? root.workspaceController.selectedSiteFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.siteOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setSiteFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { text: "Storeroom"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted; visible: root._isStockView }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; visible: root._isStockView; model: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.storeroomOptions || []) : [], root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setStoreroomFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { text: "Supplier"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted; visible: !root._isStockView }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; visible: !root._isStockView; model: root.workspaceController ? (root.workspaceController.supplierOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.supplierOptions || []) : [], root.workspaceController ? root.workspaceController.selectedSupplierFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.supplierOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setSupplierFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { text: "Limit"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted; visible: root._isStockView }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; visible: root._isStockView; model: root.workspaceController ? (root.workspaceController.limitOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.limitOptions || []) : [], root.workspaceController ? root.workspaceController.selectedLimitFilter : "200")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.limitOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setLimitFilter(String(opts[index].value || "200")) }
                    }

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.AppTheme.spacingSm
                        AppControls.SecondaryButton { Layout.fillWidth: true; text: "Clear"; iconName: "close"; onClicked: { if (root.workspaceController !== null) root.workspaceController.clearFilters(); filterPopup.close() } }
                        AppControls.PrimaryButton   { Layout.fillWidth: true; text: "Apply"; iconName: "filter"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false); onClicked: filterPopup.close() }
                    }
                }
            }

            // ── Views popup ───────────────────────────────────────────
            AppWidgets.AnchoredPopup {
                id: viewsPopup
                anchorItem: tableToolbar.viewsButtonItem; width: 220; padding: Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: Theme.AppTheme.radiusLg; color: Theme.AppTheme.surfaceRaised; border.color: Theme.AppTheme.divider; border.width: 1 }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm
                    AppControls.Label { text: "View"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.PrimaryButton   { Layout.fillWidth: true; text: "Stock Status";   iconName: "inventory";   enabled: !root._isStockView; onClicked: { if (root.workspaceController !== null) root.workspaceController.setActiveView("stock"); viewsPopup.close() } }
                    AppControls.SecondaryButton { Layout.fillWidth: true; text: "Supplier Pricing"; iconName: "procurement"; enabled:  root._isStockView; onClicked: { if (root.workspaceController !== null) root.workspaceController.setActiveView("supplier_pricing"); viewsPopup.close() } }
                }
            }

            // ── Export actions popup ──────────────────────────────────
            AppWidgets.AnchoredPopup {
                id: exportActionsPopup
                anchorItem: tableToolbar; width: 220; padding: Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: Theme.AppTheme.radiusLg; color: Theme.AppTheme.surfaceRaised; border.color: Theme.AppTheme.divider; border.width: 1 }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm
                    AppControls.Label { text: "Export"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.SecondaryButton { Layout.fillWidth: true; text: "Stock Status CSV";    iconName: "export"; enabled: root.workspaceController ? root.workspaceController.canExport : false; onClicked: { root.exportActionRequested("stockCsv");   exportActionsPopup.close() } }
                    AppControls.SecondaryButton { Layout.fillWidth: true; text: "Stock Status Excel";  iconName: "export"; enabled: root.workspaceController ? root.workspaceController.canExport : false; onClicked: { root.exportActionRequested("stockExcel"); exportActionsPopup.close() } }
                    AppControls.SecondaryButton { Layout.fillWidth: true; text: "Procurement CSV";     iconName: "export"; enabled: root.workspaceController ? root.workspaceController.canExport : false; onClicked: { root.exportActionRequested("procCsv");    exportActionsPopup.close() } }
                    AppControls.SecondaryButton { Layout.fillWidth: true; text: "Procurement Excel";   iconName: "export"; enabled: root.workspaceController ? root.workspaceController.canExport : false; onClicked: { root.exportActionRequested("procExcel");  exportActionsPopup.close() } }
                }
            }
        }
    }
}
