pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var workspaceController: null
    property var overviewModel: ({ "metrics": [] })
    property var requisitionsModel: ({ "emptyState": "No requisitions found." })
    property var purchaseOrdersModel: ({ "emptyState": "No purchase orders found." })
    property var requisitionColumns: []
    property var purchaseOrderColumns: []

    signal rowActivated(bool isRequisition, string rowId)
    signal createRequested()
    signal exportRequested()

    readonly property bool _isRequisitionsView: root.workspaceController
        ? root.workspaceController.activeView === "requisitions"
        : true

    function _optionIndex(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    readonly property var filterButtonItem: tableToolbar.filterButtonItem
    readonly property var viewsButtonItem: tableToolbar.viewsButtonItem

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: (root.workspaceController ? root.workspaceController.isLoading : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            message: "Loading procurement..."
            compact: true; modal: false
        }
        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: root.workspaceController
                ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                : false
            message: "Saving changes..."
            compact: true; modal: false
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

            onSearchChanged: function(text) { if (root.workspaceController !== null) root.workspaceController.setSearchText(text) }
            onFilterClicked: filterPopup.open()
            onViewsClicked: viewsPopup.open()
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
            onExportRequested: root.exportRequested()
            onCreateRequested: root.createRequested()
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: _requisitionsTable
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: _paginationBar.top
                visible: root._isRequisitionsView
                multiSelect: true
                columns: root.requisitionColumns
                sourceModel: root.workspaceController ? root.workspaceController.requisitionsTableModel : null
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.requisitionsModel.emptyState || "No requisitions found."
                selectedRowId: root.workspaceController ? root.workspaceController.selectedRequisitionId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedRequisitionIds || []) : []

                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectRequisition(rowId) }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.activateRequisition(rowId)
                    root.rowActivated(true, rowId)
                }
                onRowSelectionToggled: function(rowId, selected) { if (root.workspaceController !== null) root.workspaceController.setRequisitionBulkSelection(rowId, selected) }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController === null) return
                    if (allSelected) root.workspaceController.selectVisibleRequisitions()
                    else root.workspaceController.clearRequisitionBulkSelection()
                }
            }

            AppWidgets.DataTable {
                id: _purchaseOrdersTable
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: _paginationBar.top
                visible: !root._isRequisitionsView
                multiSelect: true
                columns: root.purchaseOrderColumns
                sourceModel: root.workspaceController ? root.workspaceController.purchaseOrdersTableModel : null
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.purchaseOrdersModel.emptyState || "No purchase orders found."
                selectedRowId: root.workspaceController ? root.workspaceController.selectedPurchaseOrderId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedPurchaseOrderIds || []) : []

                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectPurchaseOrder(rowId) }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.activatePurchaseOrder(rowId)
                    root.rowActivated(false, rowId)
                }
                onRowSelectionToggled: function(rowId, selected) { if (root.workspaceController !== null) root.workspaceController.setPurchaseOrderBulkSelection(rowId, selected) }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController === null) return
                    if (allSelected) root.workspaceController.selectVisiblePurchaseOrders()
                    else root.workspaceController.clearPurchaseOrderBulkSelection()
                }
            }

            AppWidgets.TablePaginationBar {
                id: _paginationBar
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
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

            // ── Filter popup ──────────────────────────────────────────────
            AppWidgets.BulkActionBar {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: _paginationBar.top
                anchors.bottomMargin: Theme.AppTheme.spacingMd
                z: 10
                active: root._isRequisitionsView
                selectedCount: root.workspaceController ? root.workspaceController.selectedRequisitionCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: [{ "id": "cancel", "label": "Cancel Selected", "icon": "reject", "danger": true, "enabled": true }]
                onCancelRequested: { if (root.workspaceController !== null) root.workspaceController.clearRequisitionBulkSelection() }
                onActionTriggered: function(actionId) {}
            }

            AppWidgets.BulkActionBar {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: _paginationBar.top
                anchors.bottomMargin: Theme.AppTheme.spacingMd
                z: 10
                active: !root._isRequisitionsView
                selectedCount: root.workspaceController ? root.workspaceController.selectedPurchaseOrderCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: [{ "id": "cancel", "label": "Cancel Selected", "icon": "reject", "danger": true, "enabled": true }]
                onCancelRequested: { if (root.workspaceController !== null) root.workspaceController.clearPurchaseOrderBulkSelection() }
                onActionTriggered: function(actionId) {}
            }

            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: tableToolbar.filterButtonItem
                width: 304; padding: Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: Theme.AppTheme.radiusLg; color: Theme.AppTheme.surfaceRaised; border.color: Theme.AppTheme.divider; border.width: 1 }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label { text: "Site"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndex(root.workspaceController ? (root.workspaceController.siteOptions || []) : [], root.workspaceController ? root.workspaceController.selectedSiteFilter : "all")
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) root.workspaceController.setSiteFilter(String(opts[index].value || "all"))
                        }
                    }

                    AppControls.Label { visible: !root._isRequisitionsView; text: "Supplier"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; visible: !root._isRequisitionsView
                        model: root.workspaceController ? (root.workspaceController.supplierOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndex(root.workspaceController ? (root.workspaceController.supplierOptions || []) : [], root.workspaceController ? root.workspaceController.selectedSupplierFilter : "all")
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.supplierOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) root.workspaceController.setSupplierFilter(String(opts[index].value || "all"))
                        }
                    }

                    AppControls.Label { text: root._isRequisitionsView ? "Requisition Status" : "PO Status"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model: root._isRequisitionsView
                            ? (root.workspaceController ? (root.workspaceController.requisitionStatusOptions || []) : [])
                            : (root.workspaceController ? (root.workspaceController.purchaseOrderStatusOptions || []) : [])
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndex(
                            root._isRequisitionsView ? (root.workspaceController ? (root.workspaceController.requisitionStatusOptions || []) : []) : (root.workspaceController ? (root.workspaceController.purchaseOrderStatusOptions || []) : []),
                            root._isRequisitionsView ? (root.workspaceController ? root.workspaceController.selectedRequisitionStatusFilter : "all") : (root.workspaceController ? root.workspaceController.selectedPurchaseOrderStatusFilter : "all")
                        )
                        onActivated: function(index) {
                            if (root.workspaceController === null) return
                            const opts = root._isRequisitionsView ? (root.workspaceController.requisitionStatusOptions || []) : (root.workspaceController.purchaseOrderStatusOptions || [])
                            if (!opts[index]) return
                            if (root._isRequisitionsView) root.workspaceController.setRequisitionStatusFilter(String(opts[index].value || "all"))
                            else root.workspaceController.setPurchaseOrderStatusFilter(String(opts[index].value || "all"))
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.AppTheme.spacingSm
                        AppControls.SecondaryButton { Layout.fillWidth: true; text: "Clear"; iconName: "close"; onClicked: { if (root.workspaceController !== null) root.workspaceController.clearFilters(); filterPopup.close() } }
                        AppControls.PrimaryButton { Layout.fillWidth: true; text: "Apply"; iconName: "filter"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false); onClicked: filterPopup.close() }
                    }
                }
            }

            // ── Views popup ───────────────────────────────────────────────
            AppWidgets.AnchoredPopup {
                id: viewsPopup
                anchorItem: tableToolbar.viewsButtonItem
                width: 220; padding: Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: Theme.AppTheme.radiusLg; color: Theme.AppTheme.surfaceRaised; border.color: Theme.AppTheme.divider; border.width: 1 }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm
                    AppControls.Label { text: "View"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.PrimaryButton { Layout.fillWidth: true; text: "Requisitions"; iconName: "register"; enabled: !root._isRequisitionsView; onClicked: { if (root.workspaceController !== null) root.workspaceController.setActiveView("requisitions"); viewsPopup.close() } }
                    AppControls.SecondaryButton { Layout.fillWidth: true; text: "Purchase Orders"; iconName: "procurement"; enabled: root._isRequisitionsView; onClicked: { if (root.workspaceController !== null) root.workspaceController.setActiveView("purchase_orders"); viewsPopup.close() } }
                }
            }

            // ── Bulk action bars ──────────────────────────────────────────
        }
    }
}
