pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Maintenance.Controllers 1.0 as MaintenanceControllers
import Maintenance.Widgets 1.0 as MaintenanceWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    property MaintenanceControllers.MaintenanceAssetsWorkspaceController workspaceController: root.maintenanceCatalog
        ? root.maintenanceCatalog.assetsWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "maintenance_management.assets",
            "title": "Assets",
            "summary": "Sites, locations, systems, assets, and component-library structures for maintenance scope.",
            "migrationStatus": "QML asset-library slice active",
            "legacyRuntimeStatus": "Existing QWidget workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var locationModel: root.workspaceController
        ? root.workspaceController.locations
        : ({
            "title": "Locations",
            "subtitle": "",
            "emptyState": "Maintenance assets desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var systemModel: root.workspaceController
        ? root.workspaceController.systems
        : ({
            "title": "Systems",
            "subtitle": "",
            "emptyState": "Maintenance assets desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var assetModel: root.workspaceController
        ? root.workspaceController.assets
        : ({
            "title": "Assets",
            "subtitle": "",
            "emptyState": "Maintenance assets desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var componentModel: root.workspaceController
        ? root.workspaceController.components
        : ({
            "title": "Components",
            "subtitle": "",
            "emptyState": "Maintenance assets desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedLocationModel: root.workspaceController
        ? root.workspaceController.selectedLocation
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a location to inspect hierarchy, lifecycle state, and update actions.",
            "fields": [],
            "state": {}
        })
    readonly property var selectedSystemModel: root.workspaceController
        ? root.workspaceController.selectedSystem
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a system to inspect hierarchy, lifecycle state, and update actions.",
            "fields": [],
            "state": {}
        })
    readonly property var selectedAssetModel: root.workspaceController
        ? root.workspaceController.selectedAsset
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select an asset to inspect anchor context, lifecycle state, and update actions.",
            "fields": [],
            "state": {}
        })
    readonly property var selectedComponentModel: root.workspaceController
        ? root.workspaceController.selectedComponent
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a component to inspect asset scope, lifecycle state, and update actions.",
            "fields": [],
            "state": {}
        })
    readonly property var _activeDetailModel: {
        if (libraryTabs.currentIndex === 1) return root.selectedSystemModel
        if (libraryTabs.currentIndex === 2) return root.selectedAssetModel
        if (libraryTabs.currentIndex === 3) return root.selectedComponentModel
        return root.selectedLocationModel
    }
    readonly property string currentCreateLabel: ({
        0: "New Location",
        1: "New System",
        2: "New Asset",
        3: "New Component"
    })[libraryTabs.currentIndex] || "New Record"

    readonly property var _locationColumns: [
        { "key": "title",       "label": "Name",   "flex": 2, "sortable": true },
        { "key": "subtitle",    "label": "Parent", "flex": 2                   },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 100, "type": "status" }
    ]
    readonly property var _systemColumns: [
        { "key": "title",       "label": "Name",     "flex": 2, "sortable": true },
        { "key": "subtitle",    "label": "Location", "flex": 2                   },
        { "key": "statusLabel", "label": "Status",   "flex": 0, "minWidth": 100, "type": "status" }
    ]
    readonly property var _assetColumns: [
        { "key": "title",       "label": "Name",   "flex": 2, "sortable": true },
        { "key": "subtitle",    "label": "System", "flex": 2                   },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 100, "type": "status" }
    ]
    readonly property var _componentColumns: [
        { "key": "title",       "label": "Name",   "flex": 2, "sortable": true },
        { "key": "subtitle",    "label": "Asset",  "flex": 2                   },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 100, "type": "status" }
    ]

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    function stateFromRecord(recordData) {
        return recordData && recordData.state ? recordData.state : (recordData || {})
    }

    function openCreateDialogForCurrentTab() {
        switch (libraryTabs.currentIndex) {
        case 0: dialogHostLoader.invoke("openCreateLocationDialog"); break
        case 1: dialogHostLoader.invoke("openCreateSystemDialog"); break
        case 2: dialogHostLoader.invoke("openCreateAssetDialog"); break
        default: dialogHostLoader.invoke("openCreateComponentDialog"); break
        }
    }

    function _openEditDialogForCurrentTab() {
        const mdl = root._activeDetailModel
        switch (libraryTabs.currentIndex) {
        case 0: dialogHostLoader.invoke("openEditLocationDialog", mdl); break
        case 1: dialogHostLoader.invoke("openEditSystemDialog", mdl); break
        case 2: dialogHostLoader.invoke("openEditAssetDialog", mdl); break
        default: dialogHostLoader.invoke("openEditComponentDialog", mdl); break
        }
    }

    function toggleLocationFromState(recordData) {
        const state = root.stateFromRecord(recordData)
        if (root.workspaceController !== null) {
            root.workspaceController.toggleLocationActive(String(state.locationId || ""), Number(state.expectedVersion || 0))
        }
    }

    function toggleSystemFromState(recordData) {
        const state = root.stateFromRecord(recordData)
        if (root.workspaceController !== null) {
            root.workspaceController.toggleSystemActive(String(state.systemId || ""), Number(state.expectedVersion || 0))
        }
    }

    function toggleAssetFromState(recordData) {
        const state = root.stateFromRecord(recordData)
        if (root.workspaceController !== null) {
            root.workspaceController.toggleAssetActive(String(state.assetId || ""), Number(state.expectedVersion || 0))
        }
    }

    function toggleComponentFromState(recordData) {
        const state = root.stateFromRecord(recordData)
        if (root.workspaceController !== null) {
            root.workspaceController.toggleComponentActive(String(state.componentId || ""), Number(state.expectedVersion || 0))
        }
    }

    function _toggleActiveForCurrentTab() {
        switch (libraryTabs.currentIndex) {
        case 0: root.toggleLocationFromState(root.selectedLocationModel); break
        case 1: root.toggleSystemFromState(root.selectedSystemModel); break
        case 2: root.toggleAssetFromState(root.selectedAssetModel); break
        default: root.toggleComponentFromState(root.selectedComponentModel); break
        }
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            AssetsDialogHost {
                siteOptions: root.workspaceController ? (root.workspaceController.formSiteOptions || []) : []
                locationOptions: root.workspaceController ? (root.workspaceController.formLocationOptions || []) : []
                parentLocationOptions: root.workspaceController ? (root.workspaceController.formParentLocationOptions || []) : []
                systemOptions: root.workspaceController ? (root.workspaceController.formSystemOptions || []) : []
                parentSystemOptions: root.workspaceController ? (root.workspaceController.formParentSystemOptions || []) : []
                assetOptions: root.workspaceController ? (root.workspaceController.formAssetOptions || []) : []
                parentAssetOptions: root.workspaceController ? (root.workspaceController.formParentAssetOptions || []) : []
                componentOptions: root.workspaceController ? (root.workspaceController.formComponentOptions || []) : []
                parentComponentOptions: root.workspaceController ? (root.workspaceController.formParentComponentOptions || []) : []
                statusOptions: root.workspaceController ? (root.workspaceController.formStatusOptions || []) : []
                criticalityOptions: root.workspaceController ? (root.workspaceController.formCriticalityOptions || []) : []
                manufacturerOptions: root.workspaceController ? (root.workspaceController.formManufacturerOptions || []) : []
                supplierOptions: root.workspaceController ? (root.workspaceController.formSupplierOptions || []) : []

                onCreateLocationRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createLocation(payload)
                }
                onUpdateLocationRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updateLocation(payload)
                }
                onCreateSystemRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createSystem(payload)
                }
                onUpdateSystemRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updateSystem(payload)
                }
                onCreateAssetRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createAsset(payload)
                }
                onUpdateAssetRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updateAsset(payload)
                }
                onCreateComponentRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createComponent(payload)
                }
                onUpdateComponentRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updateComponent(payload)
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        MaintenanceWidgets.WorkspaceStateBanner {
            Layout.fillWidth: true
            isLoading: root.workspaceController ? root.workspaceController.isLoading : false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false
            errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
            feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        MaintenanceWidgets.WorkspaceStatusSection {
            visible: false
            Layout.fillWidth: true
            migrationStatus: root.workspaceController
                ? "QML asset-library slice active"
                : (root.workspaceModel.migrationStatus || "")
            legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
            architectureStatus: "Desktop API + typed controller"
            architectureSummary: "Locations, systems, assets, and components now migrate through one typed maintenance controller backed by the maintenance assets desktop API."
        }

        TabBar {
            id: libraryTabs
            Layout.fillWidth: true
            onCurrentIndexChanged: detailPage.open = false

            TabButton { text: "Locations" }
            TabButton { text: "Systems" }
            TabButton { text: "Assets" }
            TabButton { text: "Components" }
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search assets…"
            showCreate: true
            createLabel: root.currentCreateLabel
            showFilter: true
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
            }
            onFilterClicked: filterPopup.open()
            onRefreshRequested: {
                if (root.workspaceController !== null) root.workspaceController.refresh()
            }
            onCreateRequested: root.openCreateDialogForCurrentTab()
        }

        // ── Full-width table with full-page detail view ───────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: locationsTable
                anchors.fill: parent
                visible: libraryTabs.currentIndex === 0
                columns: root._locationColumns
                sourceModel: root.workspaceController ? root.workspaceController.locationsTableModel : null
                selectedRowId: root.workspaceController ? root.workspaceController.selectedLocationId : ""

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectLocation(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectLocation(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectLocation(rowId)
                    detailPage.open = true
                }
                onSortRequested: function(key) {}
            }

            AppWidgets.DataTable {
                id: systemsTable
                anchors.fill: parent
                visible: libraryTabs.currentIndex === 1
                columns: root._systemColumns
                sourceModel: root.workspaceController ? root.workspaceController.systemsTableModel : null
                selectedRowId: root.workspaceController ? root.workspaceController.selectedSystemId : ""

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectSystem(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectSystem(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectSystem(rowId)
                    detailPage.open = true
                }
                onSortRequested: function(key) {}
            }

            AppWidgets.DataTable {
                id: assetsTable
                anchors.fill: parent
                visible: libraryTabs.currentIndex === 2
                columns: root._assetColumns
                sourceModel: root.workspaceController ? root.workspaceController.assetsTableModel : null
                selectedRowId: root.workspaceController ? root.workspaceController.selectedAssetId : ""

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectAsset(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectAsset(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectAsset(rowId)
                    detailPage.open = true
                }
                onSortRequested: function(key) {}
            }

            AppWidgets.DataTable {
                id: componentsTable
                anchors.fill: parent
                visible: libraryTabs.currentIndex === 3
                columns: root._componentColumns
                sourceModel: root.workspaceController ? root.workspaceController.componentsTableModel : null
                selectedRowId: root.workspaceController ? root.workspaceController.selectedComponentId : ""

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectComponent(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectComponent(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectComponent(rowId)
                    detailPage.open = true
                }
                onSortRequested: function(key) {}
            }

            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: tableToolbar.filterButtonItem
                width: 260
                padding: 12
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                background: Rectangle {
                    radius: Theme.AppTheme.radiusMd
                    color: Theme.AppTheme.surfaceRaised
                }

                ColumnLayout {
                    width: parent.width
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        Layout.fillWidth: true
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
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setSiteFilter(String(opts[index].value || "all"))
                        }
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "Active Status"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.activeFilterOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.activeFilterOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setActiveFilter(String(opts[index].value || "all"))
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.SecondaryButton {
                            text: "Clear"
                            iconName: "close"
                            onClicked: {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.setSiteFilter("all")
                                    root.workspaceController.setActiveFilter("all")
                                }
                                filterPopup.close()
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        AppControls.SecondaryButton {
                            text: "Close"
                            iconName: "close"
                            onClicked: filterPopup.close()
                        }
                    }
                }
            }

            AppWidgets.SectionDetailPage {
                id: detailPage
                anchors.fill: parent
                title: root._activeDetailModel.title || "Asset Details"
                open: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: ["Overview", "Details", "Actions"]

                onBackRequested: detailPage.open = false
                onEditRequested: root._openEditDialogForCurrentTab()
                onDeleteRequested: detailPage.open = false

                AssetLibraryDetailSection {
                    width: parent.width
                    detailPage: detailPage
                    detailModel: root._activeDetailModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onPrimaryActionRequested: root._openEditDialogForCurrentTab()
                    onSecondaryActionRequested: root._toggleActiveForCurrentTab()
                }
            }
        }
    }
}
