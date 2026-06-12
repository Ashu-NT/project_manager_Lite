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
    property InventoryProcurementControllers.InventoryProcurementReservationsWorkspaceController workspaceController
    property var overviewModel:      ({ "metrics": [] })
    property var reservationsModel:  ({ "emptyState": "No reservations found.", "items": [] })
    property bool detailOpen: false

    // ── Signals ───────────────────────────────────────────────────────────
    signal rowActivated()
    signal exportRequested()
    signal createRequested(string selectedItemFilter, string selectedStoreroomFilter)

    // ── Columns ───────────────────────────────────────────────────────────
    readonly property var _columns: [
        { "key": "title",             "label": "Reference",      "flex": 2,   "sortable": true },
        { "key": "subtitle",          "label": "Item / Storeroom", "flex": 1.5 },
        { "key": "remainingQtyLabel", "label": "Remaining Qty",  "flex": 1   },
        { "key": "statusLabel",       "label": "Status",         "flex": 0,   "minWidth": 90, "type": "status" }
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

        AppWidgets.LoadingOverlay { Layout.fillWidth: true; loading: (root.workspaceController ? root.workspaceController.isLoading : false) && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; message: "Loading reservations..."; compact: true; modal: false }
        AppWidgets.LoadingOverlay { Layout.fillWidth: true; loading: root.workspaceController ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0 : false; message: "Saving changes..."; compact: true; modal: false }
        AppWidgets.InlineMessage  { Layout.fillWidth: true; visible: !root.detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0; tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : "" }
        AppWidgets.InlineMessage  { Layout.fillWidth: true; visible: !root.detailOpen && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0 && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : "" }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchText:        root.workspaceController ? root.workspaceController.searchText : ""
            searchPlaceholder: "Search reservations..."
            showCreate:  true
            createLabel: "New Reservation"
            showFilter:  true
            showRefresh: true
            showExport:  true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged:    function(text) { if (root.workspaceController !== null) root.workspaceController.setSearchText(text) }
            onFilterClicked:    filterPopup.open()
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
            onExportRequested:  root.exportRequested()
            onCreateRequested:  root.createRequested(
                root.workspaceController ? root.workspaceController.selectedItemFilter    : "all",
                root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all"
            )
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: _reservationsTable
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: _paginationBar.top
                multiSelect:    true
                columns:        root._columns
                sourceModel:    root.workspaceController ? root.workspaceController.reservationsTableModel : null
                loading:        root.workspaceController ? root.workspaceController.isLoading : false
                emptyText:      root.reservationsModel.emptyState || "No reservations found."
                selectedRowId:  root.workspaceController ? root.workspaceController.selectedReservationId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedReservationIds || []) : []

                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectReservation(rowId) }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.activateReservation(rowId)
                    root.rowActivated()
                }
                onRowSelectionToggled: function(rowId, selected) { if (root.workspaceController !== null) root.workspaceController.setReservationBulkSelection(rowId, selected) }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController === null) return
                    if (allSelected) root.workspaceController.selectVisibleReservations()
                    else             root.workspaceController.clearReservationBulkSelection()
                }
            }

            AppWidgets.TablePaginationBar {
                id: _paginationBar
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                currentPage: root.workspaceController ? root.workspaceController.reservationPage      : 1
                pageSize:    root.workspaceController ? root.workspaceController.reservationPageSize   : 25
                totalItems:  root.workspaceController ? root.workspaceController.reservationTotalCount : 0
                busy:        root.workspaceController ? root.workspaceController.isBusy                : false
                onPageRequested:     function(page) { if (root.workspaceController !== null) root.workspaceController.setReservationPage(page) }
                onPageSizeRequested: function(size) { if (root.workspaceController !== null) root.workspaceController.setReservationPageSize(size) }
            }

            // ── Filter popup ──────────────────────────────────────────────
            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: tableToolbar.filterButtonItem; width: 304; padding: Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: Theme.AppTheme.radiusLg; color: Theme.AppTheme.surfaceRaised; border.color: Theme.AppTheme.divider; border.width: 1 }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label { text: "Status";   font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.statusOptions || []) : [], root.workspaceController ? root.workspaceController.selectedStatusFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.statusOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setStatusFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { text: "Item";     font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.itemOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.itemOptions || []) : [], root.workspaceController ? root.workspaceController.selectedItemFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.itemOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setItemFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { text: "Storeroom"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.storeroomOptions || []) : [], root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setStoreroomFilter(String(opts[index].value || "all")) }
                    }

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.AppTheme.spacingSm
                        AppControls.SecondaryButton { Layout.fillWidth: true; text: "Clear"; iconName: "close"; onClicked: { if (root.workspaceController !== null) root.workspaceController.clearFilters(); filterPopup.close() } }
                        AppControls.PrimaryButton   { Layout.fillWidth: true; text: "Apply"; iconName: "filter"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false); onClicked: filterPopup.close() }
                    }
                }
            }

            // ── Bulk action bar ───────────────────────────────────────────
            AppWidgets.BulkActionBar {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: _paginationBar.top; anchors.bottomMargin: Theme.AppTheme.spacingMd
                z: 10
                selectedCount: root.workspaceController ? root.workspaceController.selectedReservationCount : 0
                busy:          root.workspaceController ? root.workspaceController.isBusy : false
                actions: [{ "id": "cancel", "label": "Cancel Selected", "icon": "reject", "danger": true, "enabled": true }]
                onCancelRequested: { if (root.workspaceController !== null) root.workspaceController.clearReservationBulkSelection() }
                onActionTriggered: function(actionId) {}
            }
        }
    }
}
