pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Maintenance.Controllers 1.0 as MaintenanceControllers
import "../sections"

Item {
    id: root

    // ── Inputs ────────────────────────────────────────────────────────────
    property MaintenanceControllers.MaintenanceAssetsWorkspaceController workspaceController
    property var selectedLocationModel:  ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "emptyState": "Select a location.", "fields": [], "state": {} })
    property var selectedSystemModel:    ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "emptyState": "Select a system.",   "fields": [], "state": {} })
    property var selectedAssetModel:     ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "emptyState": "Select an asset.",    "fields": [], "state": {} })
    property var selectedComponentModel: ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "emptyState": "Select a component.", "fields": [], "state": {} })

    // ── Signals ───────────────────────────────────────────────────────────
    signal createRequested(int tabIndex)
    signal editRequested(var detailModel, int tabIndex)
    signal toggleActiveRequested(var detailModel, int tabIndex)

    // ── Derived ───────────────────────────────────────────────────────────
    readonly property var _activeDetailModel: {
        if (_tabs.currentIndex === 1) return root.selectedSystemModel
        if (_tabs.currentIndex === 2) return root.selectedAssetModel
        if (_tabs.currentIndex === 3) return root.selectedComponentModel
        return root.selectedLocationModel
    }

    readonly property string _createLabel: ({
        0: "New Location", 1: "New System", 2: "New Asset", 3: "New Component"
    })[_tabs.currentIndex] || "New Record"

    readonly property var _locationColumns: [
        { "key": "title", "label": "Name", "flex": 2, "sortable": true }, { "key": "subtitle", "label": "Parent", "flex": 2 }, { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 100, "type": "status" }
    ]
    readonly property var _systemColumns: [
        { "key": "title", "label": "Name", "flex": 2, "sortable": true }, { "key": "subtitle", "label": "Location", "flex": 2 }, { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 100, "type": "status" }
    ]
    readonly property var _assetColumns: [
        { "key": "title", "label": "Name", "flex": 2, "sortable": true }, { "key": "subtitle", "label": "System", "flex": 2 }, { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 100, "type": "status" }
    ]
    readonly property var _componentColumns: [
        { "key": "title", "label": "Name", "flex": 2, "sortable": true }, { "key": "subtitle", "label": "Asset", "flex": 2 }, { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 100, "type": "status" }
    ]

    // ── Layout ────────────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        TabBar {
            id: _tabs
            Layout.fillWidth: true
            onCurrentIndexChanged: _detailPage.open = false
            TabButton { text: "Locations"  }
            TabButton { text: "Systems"    }
            TabButton { text: "Assets"     }
            TabButton { text: "Components" }
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search assets…"
            showCreate:  true
            createLabel: root._createLabel
            showFilter:  true
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged:    function(text) { if (root.workspaceController !== null) root.workspaceController.setSearchText(text) }
            onFilterClicked:    filterPopup.open()
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
            onCreateRequested:  root.createRequested(_tabs.currentIndex)
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                anchors.fill: parent; visible: _tabs.currentIndex === 0
                columns: root._locationColumns
                sourceModel: root.workspaceController ? root.workspaceController.locationsTableModel : null
                selectedRowId: root.workspaceController ? root.workspaceController.selectedLocationId : ""
                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectLocation(rowId) }
                onRowActivated: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectLocation(rowId) }
                onViewDetailRequested: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectLocation(rowId); _detailPage.open = true }
            }
            AppWidgets.DataTable {
                anchors.fill: parent; visible: _tabs.currentIndex === 1
                columns: root._systemColumns
                sourceModel: root.workspaceController ? root.workspaceController.systemsTableModel : null
                selectedRowId: root.workspaceController ? root.workspaceController.selectedSystemId : ""
                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectSystem(rowId) }
                onRowActivated: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectSystem(rowId) }
                onViewDetailRequested: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectSystem(rowId); _detailPage.open = true }
            }
            AppWidgets.DataTable {
                anchors.fill: parent; visible: _tabs.currentIndex === 2
                columns: root._assetColumns
                sourceModel: root.workspaceController ? root.workspaceController.assetsTableModel : null
                selectedRowId: root.workspaceController ? root.workspaceController.selectedAssetId : ""
                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectAsset(rowId) }
                onRowActivated: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectAsset(rowId) }
                onViewDetailRequested: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectAsset(rowId); _detailPage.open = true }
            }
            AppWidgets.DataTable {
                anchors.fill: parent; visible: _tabs.currentIndex === 3
                columns: root._componentColumns
                sourceModel: root.workspaceController ? root.workspaceController.componentsTableModel : null
                selectedRowId: root.workspaceController ? root.workspaceController.selectedComponentId : ""
                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectComponent(rowId) }
                onRowActivated: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectComponent(rowId) }
                onViewDetailRequested: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectComponent(rowId); _detailPage.open = true }
            }

            // ── Filter popup ──────────────────────────────────────────────
            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: tableToolbar.filterButtonItem; width: 260; padding: 12
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: Theme.AppTheme.radiusMd; color: Theme.AppTheme.surfaceRaised }

                ColumnLayout {
                    width: parent.width; spacing: Theme.AppTheme.spacingSm

                    AppControls.Label { Layout.fillWidth: true; text: "Site"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.siteOptions || []) : []; textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.siteOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setSiteFilter(String(opts[index].value || "all")) }
                    }

                    AppControls.Label { Layout.fillWidth: true; text: "Active Status"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.activeFilterOptions || []) : []; textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.activeFilterOptions || []) : []; if (root.workspaceController !== null && opts[index]) root.workspaceController.setActiveFilter(String(opts[index].value || "all")) }
                    }

                    RowLayout {
                        Layout.fillWidth: true; spacing: Theme.AppTheme.spacingSm
                        AppControls.SecondaryButton {
                            text: "Clear"; iconName: "close"
                            onClicked: { if (root.workspaceController !== null) { root.workspaceController.setSiteFilter("all"); root.workspaceController.setActiveFilter("all") }; filterPopup.close() }
                        }
                        Item { Layout.fillWidth: true }
                        AppControls.SecondaryButton { text: "Close"; iconName: "close"; onClicked: filterPopup.close() }
                    }
                }
            }

            // ── Inline detail page ────────────────────────────────────────
            AppWidgets.SectionDetailPage {
                id: _detailPage
                anchors.fill: parent
                title:    root._activeDetailModel.title || "Asset Details"
                open:     false
                isBusy:   root.workspaceController ? root.workspaceController.isBusy : false
                sections: ["Overview", "Details", "Actions"]

                onBackRequested:   _detailPage.open = false
                onEditRequested:   root.editRequested(root._activeDetailModel, _tabs.currentIndex)
                onDeleteRequested: _detailPage.open = false

                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: _detailPage.open && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0; tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : "" }
                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: _detailPage.open && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0 && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : "" }

                AssetLibraryDetailSection {
                    width: parent ? parent.width : 0
                    detailPage:  _detailPage
                    detailModel: root._activeDetailModel
                    isBusy:      root.workspaceController ? root.workspaceController.isBusy : false
                    onPrimaryActionRequested:   root.editRequested(root._activeDetailModel, _tabs.currentIndex)
                    onSecondaryActionRequested: root.toggleActiveRequested(root._activeDetailModel, _tabs.currentIndex)
                }
            }
        }
    }
}
