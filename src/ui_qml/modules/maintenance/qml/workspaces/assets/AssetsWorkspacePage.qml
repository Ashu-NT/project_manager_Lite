import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
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
    readonly property string currentCreateLabel: ({
        0: "New Location",
        1: "New System",
        2: "New Asset",
        3: "New Component"
    })[libraryTabs.currentIndex] || "New Record"

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    function stateFromRecord(recordData) {
        return recordData && recordData.state ? recordData.state : (recordData || {})
    }

    function openCreateDialogForCurrentTab() {
        switch (libraryTabs.currentIndex) {
        case 0:
            dialogHost.openCreateLocationDialog()
            break
        case 1:
            dialogHost.openCreateSystemDialog()
            break
        case 2:
            dialogHost.openCreateAssetDialog()
            break
        default:
            dialogHost.openCreateComponentDialog()
            break
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

    AssetsDialogHost {
        id: dialogHost

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
            if (root.workspaceController !== null) {
                root.workspaceController.createLocation(payload)
            }
        }

        onUpdateLocationRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateLocation(payload)
            }
        }

        onCreateSystemRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createSystem(payload)
            }
        }

        onUpdateSystemRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateSystem(payload)
            }
        }

        onCreateAssetRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createAsset(payload)
            }
        }

        onUpdateAssetRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateAsset(payload)
            }
        }

        onCreateComponentRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createComponent(payload)
            }
        }

        onUpdateComponentRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateComponent(payload)
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: 12

            AssetsMetricsSection {
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
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML asset-library slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Locations, systems, assets, and components now migrate through one typed maintenance controller backed by the maintenance assets desktop API."
            }

            AssetsFiltersSection {
                Layout.fillWidth: true
                siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                activeFilterOptions: root.workspaceController ? (root.workspaceController.activeFilterOptions || []) : []
                selectedSiteFilter: root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                selectedActiveFilter: root.workspaceController ? root.workspaceController.selectedActiveFilter : "all"
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onSearchTextUpdated: function(searchText) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSearchText(searchText)
                    }
                }

                onSiteFilterUpdated: function(siteId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSiteFilter(siteId)
                    }
                }

                onActiveFilterUpdated: function(activeFilter) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setActiveFilter(activeFilter)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                TabBar {
                    id: libraryTabs
                    Layout.fillWidth: true

                    TabButton { text: "Locations" }
                    TabButton { text: "Systems" }
                    TabButton { text: "Assets" }
                    TabButton { text: "Components" }
                }

                AppControls.PrimaryButton {
                    text: root.currentCreateLabel
                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                    onClicked: root.openCreateDialogForCurrentTab()
                }
            }

            StackLayout {
                Layout.fillWidth: true
                currentIndex: libraryTabs.currentIndex

                Item {
                    implicitWidth: locationLayout.implicitWidth
                    implicitHeight: locationLayout.implicitHeight

                    GridLayout {
                        id: locationLayout

                        width: parent.width
                        columns: root.width > 1180 ? 2 : 1
                        columnSpacing: 12
                        rowSpacing: 12

                        AssetLibraryCatalogSection {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            catalogModel: root.locationModel
                            selectedItemId: root.workspaceController ? root.workspaceController.selectedLocationId : ""
                            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                            onItemChosen: function(itemId) {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.selectLocation(itemId)
                                }
                            }

                            onPrimaryActionChosen: function(itemData) {
                                if (itemData && itemData.id && root.workspaceController !== null) {
                                    root.workspaceController.selectLocation(itemData.id)
                                }
                                dialogHost.openEditLocationDialog(itemData)
                            }

                            onSecondaryActionChosen: function(itemData) {
                                if (itemData && itemData.id && root.workspaceController !== null) {
                                    root.workspaceController.selectLocation(itemData.id)
                                }
                                root.toggleLocationFromState(itemData)
                            }
                        }

                        AssetLibraryDetailSection {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            emptyTitle: "No location selected"
                            detailModel: root.selectedLocationModel
                            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                            onPrimaryActionRequested: dialogHost.openEditLocationDialog(root.selectedLocationModel)
                            onSecondaryActionRequested: root.toggleLocationFromState(root.selectedLocationModel)
                        }
                    }
                }

                Item {
                    implicitWidth: systemLayout.implicitWidth
                    implicitHeight: systemLayout.implicitHeight

                    GridLayout {
                        id: systemLayout

                        width: parent.width
                        columns: root.width > 1180 ? 2 : 1
                        columnSpacing: 12
                        rowSpacing: 12

                        AssetLibraryCatalogSection {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            catalogModel: root.systemModel
                            selectedItemId: root.workspaceController ? root.workspaceController.selectedSystemId : ""
                            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                            onItemChosen: function(itemId) {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.selectSystem(itemId)
                                }
                            }

                            onPrimaryActionChosen: function(itemData) {
                                if (itemData && itemData.id && root.workspaceController !== null) {
                                    root.workspaceController.selectSystem(itemData.id)
                                }
                                dialogHost.openEditSystemDialog(itemData)
                            }

                            onSecondaryActionChosen: function(itemData) {
                                if (itemData && itemData.id && root.workspaceController !== null) {
                                    root.workspaceController.selectSystem(itemData.id)
                                }
                                root.toggleSystemFromState(itemData)
                            }
                        }

                        AssetLibraryDetailSection {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            emptyTitle: "No system selected"
                            detailModel: root.selectedSystemModel
                            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                            onPrimaryActionRequested: dialogHost.openEditSystemDialog(root.selectedSystemModel)
                            onSecondaryActionRequested: root.toggleSystemFromState(root.selectedSystemModel)
                        }
                    }
                }

                Item {
                    implicitWidth: assetLayout.implicitWidth
                    implicitHeight: assetLayout.implicitHeight

                    GridLayout {
                        id: assetLayout

                        width: parent.width
                        columns: root.width > 1180 ? 2 : 1
                        columnSpacing: 12
                        rowSpacing: 12

                        AssetLibraryCatalogSection {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            catalogModel: root.assetModel
                            selectedItemId: root.workspaceController ? root.workspaceController.selectedAssetId : ""
                            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                            onItemChosen: function(itemId) {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.selectAsset(itemId)
                                }
                            }

                            onPrimaryActionChosen: function(itemData) {
                                if (itemData && itemData.id && root.workspaceController !== null) {
                                    root.workspaceController.selectAsset(itemData.id)
                                }
                                dialogHost.openEditAssetDialog(itemData)
                            }

                            onSecondaryActionChosen: function(itemData) {
                                if (itemData && itemData.id && root.workspaceController !== null) {
                                    root.workspaceController.selectAsset(itemData.id)
                                }
                                root.toggleAssetFromState(itemData)
                            }
                        }

                        AssetLibraryDetailSection {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            emptyTitle: "No asset selected"
                            detailModel: root.selectedAssetModel
                            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                            onPrimaryActionRequested: dialogHost.openEditAssetDialog(root.selectedAssetModel)
                            onSecondaryActionRequested: root.toggleAssetFromState(root.selectedAssetModel)
                        }
                    }
                }

                Item {
                    implicitWidth: componentLayout.implicitWidth
                    implicitHeight: componentLayout.implicitHeight

                    GridLayout {
                        id: componentLayout

                        width: parent.width
                        columns: root.width > 1180 ? 2 : 1
                        columnSpacing: 12
                        rowSpacing: 12

                        AssetLibraryCatalogSection {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            catalogModel: root.componentModel
                            selectedItemId: root.workspaceController ? root.workspaceController.selectedComponentId : ""
                            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                            onItemChosen: function(itemId) {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.selectComponent(itemId)
                                }
                            }

                            onPrimaryActionChosen: function(itemData) {
                                if (itemData && itemData.id && root.workspaceController !== null) {
                                    root.workspaceController.selectComponent(itemData.id)
                                }
                                dialogHost.openEditComponentDialog(itemData)
                            }

                            onSecondaryActionChosen: function(itemData) {
                                if (itemData && itemData.id && root.workspaceController !== null) {
                                    root.workspaceController.selectComponent(itemData.id)
                                }
                                root.toggleComponentFromState(itemData)
                            }
                        }

                        AssetLibraryDetailSection {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            emptyTitle: "No component selected"
                            detailModel: root.selectedComponentModel
                            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                            onPrimaryActionRequested: dialogHost.openEditComponentDialog(root.selectedComponentModel)
                            onSecondaryActionRequested: root.toggleComponentFromState(root.selectedComponentModel)
                        }
                    }
                }
            }
        }
    }
}
