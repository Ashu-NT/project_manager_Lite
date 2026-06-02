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
    property var storeroomsModel:   ({ "emptyState": "No storerooms configured.", "items": [] })
    property var foundationModel:   ({ "locations": [], "locationTypeOptions": [] })
    property string selectedLocationId: ""
    property bool detailOpen: false

    // ── View state (readable by parent via id binding) ────────────────────
    property string warehouseView: "storerooms"
    readonly property bool isStoreroomsView: root.warehouseView === "storerooms"

    // ── Signals ───────────────────────────────────────────────────────────
    signal rowActivated()
    signal createStoreroomRequested()
    signal createLocationRequested(string selectedStoreroomFilter)

    // ── Column definitions ────────────────────────────────────────────────
    readonly property var _storeroomColumns: [
        { "key": "title",         "label": "Storeroom", "flex": 2,   "sortable": true },
        { "key": "storeroomCode", "label": "Code",      "flex": 1   },
        { "key": "siteLabel",     "label": "Site",      "flex": 1.5 },
        { "key": "statusLabel",   "label": "Status",    "flex": 0,   "minWidth": 90, "type": "status" }
    ]
    readonly property var _locationColumns: [
        { "key": "title",       "label": "Location",  "flex": 2,   "sortable": true },
        { "key": "subtitle",    "label": "Storeroom", "flex": 1.5 },
        { "key": "statusLabel", "label": "Type",      "flex": 0,   "minWidth": 100, "type": "status" },
        { "key": "metaText",    "label": "Active",    "flex": 0,   "minWidth": 80  }
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

        AppWidgets.LoadingOverlay { Layout.fillWidth: true; loading: (root.workspaceController ? root.workspaceController.isLoading : false) && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; message: "Loading warehouses..."; compact: true; modal: false }
        AppWidgets.LoadingOverlay { Layout.fillWidth: true; loading: root.workspaceController ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0 : false; message: "Saving changes..."; compact: true; modal: false }
        AppWidgets.InlineMessage  { Layout.fillWidth: true; visible: !root.detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0; tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : "" }
        AppWidgets.InlineMessage  { Layout.fillWidth: true; visible: !root.detailOpen && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0 && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : "" }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchText:        root.workspaceController ? root.workspaceController.searchText : ""
            searchPlaceholder: root.isStoreroomsView ? "Search storerooms..." : "Search locations..."
            showCreate:  true
            createLabel: root.isStoreroomsView ? "New Storeroom" : "New Location"
            showFilter:  true
            showViews:   true
            showRefresh: true
            showExport:  false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged:    function(text) { if (root.workspaceController !== null) root.workspaceController.setSearchText(text) }
            onFilterClicked:    filterPopup.open()
            onViewsClicked:     viewsPopup.open()
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
            onCreateRequested: {
                if (root.isStoreroomsView) root.createStoreroomRequested()
                else root.createLocationRequested(root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all")
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: _paginationBar.top
                visible:    root.isStoreroomsView
                multiSelect: false
                columns:    root._storeroomColumns
                sourceModel: root.workspaceController ? root.workspaceController.storeroomsTableModel : null
                loading:     root.workspaceController ? root.workspaceController.isLoading : false
                emptyText:   root.storeroomsModel.emptyState || "No storerooms configured."
                selectedRowId: root.workspaceController ? root.workspaceController.selectedStoreroomId : ""
                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectStoreroom(rowId) }
                onRowActivated: function(rowId) { if (root.workspaceController !== null) root.workspaceController.activateStoreroom(rowId); root.rowActivated() }
            }

            AppWidgets.DataTable {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: _paginationBar.top
                visible:    !root.isStoreroomsView
                multiSelect: false
                columns:    root._locationColumns
                sourceModel: root.workspaceController ? root.workspaceController.foundationTableModel : null
                loading:     root.workspaceController ? root.workspaceController.isLoading : false
                emptyText:   "No storage locations found."
                selectedRowId: root.selectedLocationId
                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectLocation(rowId) }
                onRowActivated: function(rowId) { if (root.workspaceController !== null) root.workspaceController.activateLocation(rowId); root.rowActivated() }
            }

            AppWidgets.TablePaginationBar {
                id: _paginationBar
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                currentPage: root.isStoreroomsView ? (root.workspaceController ? root.workspaceController.storeroomPage : 1) : (root.workspaceController ? root.workspaceController.locationPage : 1)
                pageSize:    root.isStoreroomsView ? (root.workspaceController ? root.workspaceController.storeroomPageSize : 25) : (root.workspaceController ? root.workspaceController.locationPageSize : 25)
                totalItems:  root.isStoreroomsView ? (root.workspaceController ? root.workspaceController.storeroomTotalCount : 0) : (root.workspaceController ? root.workspaceController.locationTotalCount : 0)
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                onPageRequested: function(page) { if (root.workspaceController === null) return; if (root.isStoreroomsView) root.workspaceController.setStoreroomPage(page); else root.workspaceController.setLocationPage(page) }
                onPageSizeRequested: function(size) { if (root.workspaceController === null) return; if (root.isStoreroomsView) root.workspaceController.setStoreroomPageSize(size); else root.workspaceController.setLocationPageSize(size) }
            }

            // ── Filter popup ──────────────────────────────────────────
            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: tableToolbar.filterButtonItem; width: 304; padding: Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: Theme.AppTheme.radiusLg; color: Theme.AppTheme.surfaceRaised; border.color: Theme.AppTheme.divider; border.width: 1 }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label { text: "Site";          font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.siteOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.siteOptions || []) : [], root.workspaceController ? root.workspaceController.selectedSiteFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.siteOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setSiteFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { text: "Status";        font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.activeOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.activeOptions || []) : [], root.workspaceController ? root.workspaceController.selectedActiveFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.activeOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setActiveFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { text: "Storeroom";     font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted; visible: !root.isStoreroomsView }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; visible: !root.isStoreroomsView; model: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.storeroomOptions || []) : [], root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all")
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setStoreroomFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { text: "Location Type"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted; visible: !root.isStoreroomsView }
                    AppControls.ComboBox { Layout.fillWidth: true; visible: !root.isStoreroomsView; model: root.foundationModel.locationTypeOptions || []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false) }

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
                    AppControls.PrimaryButton   { Layout.fillWidth: true; text: "Storerooms"; iconName: "location";  enabled: !root.isStoreroomsView; onClicked: { root.warehouseView = "storerooms"; viewsPopup.close() } }
                    AppControls.SecondaryButton { Layout.fillWidth: true; text: "Locations";  iconName: "inventory"; enabled:  root.isStoreroomsView; onClicked: { root.warehouseView = "locations"; viewsPopup.close() } }
                }
            }
        }
    }
}
