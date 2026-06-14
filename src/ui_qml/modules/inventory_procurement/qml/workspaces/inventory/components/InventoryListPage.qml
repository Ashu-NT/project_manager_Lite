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
    property InventoryProcurementControllers.InventoryProcurementInventoryWorkspaceController workspaceController
    property var overviewModel:    ({ "metrics": [] })
    property var balancesModel:    ({ "emptyState": "No stock balances.", "items": [] })
    property var storeroomsModel:  ({ "emptyState": "No storerooms configured.", "items": [] })
    property var selectedBalanceModel:  ({ "id": "", "fields": [], "state": {} })
    property var selectedStoreroomModel: ({ "id": "", "fields": [], "state": {} })
    property bool detailOpen: false

    // ── Signals ───────────────────────────────────────────────────────────
    signal rowActivated()
    signal exportRequested()
    signal createStoreroomRequested()
    signal openOpeningBalanceDialogRequested(var balanceModel, var storeroomModel, string itemFilter)
    signal openAdjustmentDialogRequested(var balanceModel)

    // ── Derived ───────────────────────────────────────────────────────────
    readonly property bool _isBalancesView: root.workspaceController
        ? root.workspaceController.activeView === "balances"
        : true

    readonly property var _balanceColumns: [
        { "key": "title",          "label": "Item Name", "flex": 2,   "sortable": true },
        { "key": "storeroomLabel", "label": "Storeroom", "flex": 1.5 },
        { "key": "onHandQtyLabel", "label": "On Hand",   "flex": 1   },
        { "key": "statusLabel",    "label": "Status",    "flex": 0,   "minWidth": 90, "type": "status" }
    ]
    readonly property var _storeroomColumns: [
        { "key": "title",         "label": "Storeroom", "flex": 2,   "sortable": true },
        { "key": "storeroomCode", "label": "Code",      "flex": 1   },
        { "key": "siteLabel",     "label": "Site",      "flex": 1.5 },
        { "key": "statusLabel",   "label": "Status",    "flex": 0,   "minWidth": 90, "type": "status" }
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

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: (root.workspaceController ? root.workspaceController.isLoading : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            message: "Loading inventory..."
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
            visible: !root.detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
            tone: "danger"
            message: root.workspaceController ? root.workspaceController.errorMessage : ""
        }
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: !root.detailOpen
                && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "success"
            message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchText:        root.workspaceController ? root.workspaceController.searchText : ""
            searchPlaceholder: root._isBalancesView ? "Search stock balances..." : "Search storerooms..."
            showCreate:  !root._isBalancesView
            createLabel: "New Storeroom"
            showFilter:  true
            showViews:   true
            showRefresh: true
            showExport:  true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged:   function(text) { if (root.workspaceController !== null) root.workspaceController.setSearchText(text) }
            onFilterClicked:   filterPopup.open()
            onViewsClicked:    viewsPopup.open()
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
            onExportRequested: root.exportRequested()
            onCreateRequested: root.createStoreroomRequested()
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: _balancesTable
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: _paginationBar.top
                visible:        root._isBalancesView
                multiSelect:    true
                columns:        root._balanceColumns
                sourceModel:    root.workspaceController ? root.workspaceController.balancesTableModel : null
                loading:        root.workspaceController ? root.workspaceController.isLoading : false
                emptyText:      root.balancesModel.emptyState || "No stock balances."
                selectedRowId:  root.workspaceController ? root.workspaceController.selectedBalanceId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedBalanceIds || []) : []

                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectBalance(rowId) }
                onRowActivated: function(rowId) { if (root.workspaceController !== null) root.workspaceController.activateBalance(rowId); root.rowActivated() }
                onRowSelectionToggled: function(rowId, selected) { if (root.workspaceController !== null) root.workspaceController.setBalanceBulkSelection(rowId, selected) }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController === null) return
                    if (allSelected) root.workspaceController.selectVisibleBalances()
                    else             root.workspaceController.clearBalanceBulkSelection()
                }
            }

            AppWidgets.DataTable {
                id: _storeroomsTable
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: _paginationBar.top
                visible:        !root._isBalancesView
                multiSelect:    true
                columns:        root._storeroomColumns
                sourceModel:    root.workspaceController ? root.workspaceController.storeroomsTableModel : null
                loading:        root.workspaceController ? root.workspaceController.isLoading : false
                emptyText:      root.storeroomsModel.emptyState || "No storerooms configured."
                selectedRowId:  root.workspaceController ? root.workspaceController.selectedStoreroomId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedStoreroomIds || []) : []

                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectStoreroom(rowId) }
                onRowActivated: function(rowId) { if (root.workspaceController !== null) root.workspaceController.activateStoreroom(rowId); root.rowActivated() }
                onRowSelectionToggled: function(rowId, selected) { if (root.workspaceController !== null) root.workspaceController.setStoreroomBulkSelection(rowId, selected) }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController === null) return
                    if (allSelected) root.workspaceController.selectVisibleStorerooms()
                    else             root.workspaceController.clearStoreroomBulkSelection()
                }
            }

            AppWidgets.TablePaginationBar {
                id: _paginationBar
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                currentPage: root._isBalancesView ? (root.workspaceController ? root.workspaceController.balancePage : 1) : (root.workspaceController ? root.workspaceController.storeroomPage : 1)
                pageSize:    root._isBalancesView ? (root.workspaceController ? root.workspaceController.balancePageSize : 25) : (root.workspaceController ? root.workspaceController.storeroomPageSize : 25)
                totalItems:  root._isBalancesView ? (root.workspaceController ? root.workspaceController.balanceTotalCount : 0) : (root.workspaceController ? root.workspaceController.storeroomTotalCount : 0)
                busy: root.workspaceController ? root.workspaceController.isBusy : false

                onPageRequested: function(page) {
                    if (root.workspaceController === null) return
                    if (root._isBalancesView) root.workspaceController.setBalancePage(page)
                    else                      root.workspaceController.setStoreroomPage(page)
                }
                onPageSizeRequested: function(size) {
                    if (root.workspaceController === null) return
                    if (root._isBalancesView) root.workspaceController.setBalancePageSize(size)
                    else                      root.workspaceController.setStoreroomPageSize(size)
                }
            }

            // ── Filter popup ──────────────────────────────────────────
            AppWidgets.BulkActionBar {
                id: _balanceBulkBar
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: _paginationBar.top
                anchors.bottomMargin: Theme.AppTheme.spacingMd
                z: 10
                active: root._isBalancesView
                selectedCount: root.workspaceController ? root.workspaceController.selectedBalanceCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: [
                    { "id": "opening_balance", "label": "Opening Balance", "icon": "add", "danger": false, "enabled": true },
                    { "id": "adjustment", "label": "Adjust", "icon": "edit", "danger": false, "enabled": true }
                ]

                onCancelRequested: { if (root.workspaceController !== null) root.workspaceController.clearBalanceBulkSelection() }
                onActionTriggered: function(actionId) {
                    if (actionId === "opening_balance")
                        root.openOpeningBalanceDialogRequested(root.selectedBalanceModel, root.selectedStoreroomModel, root.workspaceController ? root.workspaceController.selectedItemFilter : "all")
                    else if (actionId === "adjustment")
                        root.openAdjustmentDialogRequested(root.selectedBalanceModel)
                }
            }

            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: tableToolbar.filterButtonItem; width: 304; padding: Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: Theme.AppTheme.radiusLg; color: Theme.AppTheme.surfaceRaised; border.color: Theme.AppTheme.divider; border.width: 1 }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label { text: "Site";      font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.siteOptions || []) : []; textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.siteOptions || []) : [], root.workspaceController ? root.workspaceController.selectedSiteFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.siteOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setSiteFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { text: "Status";    font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.activeOptions || []) : []; textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.activeOptions || []) : [], root.workspaceController ? root.workspaceController.selectedActiveFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.activeOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setActiveFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { text: "Storeroom"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted; visible: root._isBalancesView }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; visible: root._isBalancesView; model: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []; textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.storeroomOptions || []) : [], root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setStoreroomFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { text: "Item";      font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted; visible: root._isBalancesView }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; visible: root._isBalancesView; model: root.workspaceController ? (root.workspaceController.itemOptions || []) : []; textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.itemOptions || []) : [], root.workspaceController ? root.workspaceController.selectedItemFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.itemOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setItemFilter(String(opts[index].value || "all")) }
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
                    AppControls.PrimaryButton   { Layout.fillWidth: true; text: "Stock Balances"; iconName: "inventory"; enabled: !root._isBalancesView; onClicked: { if (root.workspaceController !== null) root.workspaceController.setActiveView("balances"); viewsPopup.close() } }
                    AppControls.SecondaryButton { Layout.fillWidth: true; text: "Storerooms";     iconName: "location";  enabled:  root._isBalancesView; onClicked: { if (root.workspaceController !== null) root.workspaceController.setActiveView("storerooms"); viewsPopup.close() } }
                }
            }

            // ── Bulk action bar (balances) ────────────────────────────
        }
    }
}
