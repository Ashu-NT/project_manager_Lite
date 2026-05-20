import QtQuick
import Maintenance.Dialogs 1.0 as MaintenanceDialogs

Item {
    id: root

    property var siteOptions: []
    property var locationOptions: []
    property var systemOptions: []
    property var assetOptions: []
    property var componentOptions: []
    property var sourceTypeOptions: []
    property var priorityOptions: []
    property var statusOptions: []

    signal createRequested(var payload)
    signal updateRequested(var payload)
    signal statusChangeRequested(string workRequestId, string statusValue, int expectedVersion)

    function openCreateDialog() {
        editorDialog.modeTitle = "Create Work Request"
        editorDialog.workRequestData = ({})
        editorDialog.open()
    }

    function openEditDialog(workRequestData) {
        editorDialog.modeTitle = "Edit Work Request"
        editorDialog.workRequestData = workRequestData || ({})
        editorDialog.open()
    }

    function openStatusDialog(workRequestData) {
        statusDialog.workRequestData = workRequestData || ({})
        statusDialog.open()
    }

    MaintenanceDialogs.WorkRequestEditorDialog {
        id: editorDialog
        objectName: "workRequestEditorDialog"

        siteOptions: root.siteOptions
        locationOptions: root.locationOptions
        systemOptions: root.systemOptions
        assetOptions: root.assetOptions
        componentOptions: root.componentOptions
        sourceTypeOptions: root.sourceTypeOptions
        priorityOptions: root.priorityOptions

        onSubmitted: function(payload) {
            if (editorDialog.modeTitle === "Create Work Request") {
                root.createRequested(payload)
            } else {
                root.updateRequested(payload)
            }
            editorDialog.close()
        }
    }

    MaintenanceDialogs.WorkRequestStatusDialog {
        id: statusDialog
        objectName: "workRequestStatusDialog"

        statusOptions: root.statusOptions

        onSubmitted: function(statusValue) {
            const state = statusDialog.workRequestData && statusDialog.workRequestData.state
                ? statusDialog.workRequestData.state
                : (statusDialog.workRequestData || {})
            root.statusChangeRequested(
                String(state.workRequestId || ""),
                String(statusValue || ""),
                Number(state.expectedVersion || 0)
            )
            statusDialog.close()
        }
    }
}
