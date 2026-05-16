import QtQuick
import Maintenance.Dialogs 1.0 as MaintenanceDialogs

Item {
    id: root

    property var siteOptions: []
    property var locationOptions: []
    property var parentLocationOptions: []
    property var systemOptions: []
    property var parentSystemOptions: []
    property var assetOptions: []
    property var parentAssetOptions: []
    property var componentOptions: []
    property var parentComponentOptions: []
    property var statusOptions: []
    property var criticalityOptions: []
    property var manufacturerOptions: []
    property var supplierOptions: []

    signal createLocationRequested(var payload)
    signal updateLocationRequested(var payload)
    signal createSystemRequested(var payload)
    signal updateSystemRequested(var payload)
    signal createAssetRequested(var payload)
    signal updateAssetRequested(var payload)
    signal createComponentRequested(var payload)
    signal updateComponentRequested(var payload)

    function openCreateLocationDialog() {
        locationEditor.modeTitle = "Create Location"
        locationEditor.recordState = ({})
        locationEditor.open()
    }

    function openEditLocationDialog(recordData) {
        locationEditor.modeTitle = "Edit Location"
        locationEditor.recordState = recordData && recordData.state ? recordData.state : (recordData || {})
        locationEditor.open()
    }

    function openCreateSystemDialog() {
        systemEditor.modeTitle = "Create System"
        systemEditor.recordState = ({})
        systemEditor.open()
    }

    function openEditSystemDialog(recordData) {
        systemEditor.modeTitle = "Edit System"
        systemEditor.recordState = recordData && recordData.state ? recordData.state : (recordData || {})
        systemEditor.open()
    }

    function openCreateAssetDialog() {
        assetEditor.modeTitle = "Create Asset"
        assetEditor.recordState = ({})
        assetEditor.open()
    }

    function openEditAssetDialog(recordData) {
        assetEditor.modeTitle = "Edit Asset"
        assetEditor.recordState = recordData && recordData.state ? recordData.state : (recordData || {})
        assetEditor.open()
    }

    function openCreateComponentDialog() {
        componentEditor.modeTitle = "Create Component"
        componentEditor.recordState = ({})
        componentEditor.open()
    }

    function openEditComponentDialog(recordData) {
        componentEditor.modeTitle = "Edit Component"
        componentEditor.recordState = recordData && recordData.state ? recordData.state : (recordData || {})
        componentEditor.open()
    }

    MaintenanceDialogs.LocationEditorDialog {
        id: locationEditor

        siteOptions: root.siteOptions
        parentLocationOptions: root.parentLocationOptions
        statusOptions: root.statusOptions
        criticalityOptions: root.criticalityOptions

        onSubmitted: function(payload) {
            if (locationEditor.modeTitle === "Create Location") {
                root.createLocationRequested(payload)
            } else {
                root.updateLocationRequested(payload)
            }
            locationEditor.close()
        }
    }

    MaintenanceDialogs.SystemEditorDialog {
        id: systemEditor

        siteOptions: root.siteOptions
        locationOptions: root.locationOptions
        parentSystemOptions: root.parentSystemOptions
        statusOptions: root.statusOptions
        criticalityOptions: root.criticalityOptions

        onSubmitted: function(payload) {
            if (systemEditor.modeTitle === "Create System") {
                root.createSystemRequested(payload)
            } else {
                root.updateSystemRequested(payload)
            }
            systemEditor.close()
        }
    }

    MaintenanceDialogs.AssetEditorDialog {
        id: assetEditor

        siteOptions: root.siteOptions
        locationOptions: root.locationOptions
        systemOptions: root.systemOptions
        parentAssetOptions: root.parentAssetOptions
        statusOptions: root.statusOptions
        criticalityOptions: root.criticalityOptions
        manufacturerOptions: root.manufacturerOptions
        supplierOptions: root.supplierOptions

        onSubmitted: function(payload) {
            if (assetEditor.modeTitle === "Create Asset") {
                root.createAssetRequested(payload)
            } else {
                root.updateAssetRequested(payload)
            }
            assetEditor.close()
        }
    }

    MaintenanceDialogs.ComponentEditorDialog {
        id: componentEditor

        assetOptions: root.assetOptions
        parentComponentOptions: root.parentComponentOptions
        statusOptions: root.statusOptions
        manufacturerOptions: root.manufacturerOptions
        supplierOptions: root.supplierOptions

        onSubmitted: function(payload) {
            if (componentEditor.modeTitle === "Create Component") {
                root.createComponentRequested(payload)
            } else {
                root.updateComponentRequested(payload)
            }
            componentEditor.close()
        }
    }
}
