import QtQuick
import Maintenance.Dialogs 1.0 as MaintenanceDialogs

Item {
    id: root

    property var workspaceController: null
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

    function _handleResult(dialog, result) {
        if (!result || result.ok === false) {
            dialog.errorMessage = String((result && (result.error || result.message)) || "Operation failed. Please try again.")
        } else {
            dialog.errorMessage = ""
            dialog.close()
        }
    }

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
        objectName: "locationEditorDialog"

        siteOptions: root.siteOptions
        parentLocationOptions: root.parentLocationOptions
        statusOptions: root.statusOptions
        criticalityOptions: root.criticalityOptions

        onSubmitted: function(payload) {
            if (locationEditor.modeTitle === "Create Location") {
                root._handleResult(locationEditor, root.workspaceController.createLocation(payload))
            } else {
                root._handleResult(locationEditor, root.workspaceController.updateLocation(payload))
            }
        }
    }

    MaintenanceDialogs.SystemEditorDialog {
        id: systemEditor
        objectName: "systemEditorDialog"

        siteOptions: root.siteOptions
        locationOptions: root.locationOptions
        parentSystemOptions: root.parentSystemOptions
        statusOptions: root.statusOptions
        criticalityOptions: root.criticalityOptions

        onSubmitted: function(payload) {
            if (systemEditor.modeTitle === "Create System") {
                root._handleResult(systemEditor, root.workspaceController.createSystem(payload))
            } else {
                root._handleResult(systemEditor, root.workspaceController.updateSystem(payload))
            }
        }
    }

    MaintenanceDialogs.AssetEditorDialog {
        id: assetEditor
        objectName: "assetEditorDialog"

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
                root._handleResult(assetEditor, root.workspaceController.createAsset(payload))
            } else {
                root._handleResult(assetEditor, root.workspaceController.updateAsset(payload))
            }
        }
    }

    MaintenanceDialogs.ComponentEditorDialog {
        id: componentEditor
        objectName: "componentEditorDialog"

        assetOptions: root.assetOptions
        parentComponentOptions: root.parentComponentOptions
        statusOptions: root.statusOptions
        manufacturerOptions: root.manufacturerOptions
        supplierOptions: root.supplierOptions

        onSubmitted: function(payload) {
            if (componentEditor.modeTitle === "Create Component") {
                root._handleResult(componentEditor, root.workspaceController.createComponent(payload))
            } else {
                root._handleResult(componentEditor, root.workspaceController.updateComponent(payload))
            }
        }
    }
}
