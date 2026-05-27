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
    property var sourceWorkRequestOptions: []
    property var workOrderTypeOptions: []
    property var priorityOptions: []
    property var statusOptions: []
    property var vendorOptions: []

    signal createRequested(var payload)
    signal updateRequested(var payload)
    signal statusChangeRequested(string workOrderId, string statusValue, int expectedVersion)

    function openCreateDialog() {
        editorDialog.modeTitle = "Create Work Order"
        editorDialog.workOrderData = ({})
        editorDialog.open()
    }

    function openEditDialog(workOrderData) {
        editorDialog.modeTitle = "Edit Work Order"
        editorDialog.workOrderData = workOrderData || ({})
        editorDialog.open()
    }

    function openStatusDialog(workOrderData) {
        statusDialog.workOrderData = workOrderData || ({})
        statusDialog.open()
    }

    MaintenanceDialogs.WorkOrderEditorDialog {
        id: editorDialog
        objectName: "workOrderEditorDialog"

        siteOptions: root.siteOptions
        locationOptions: root.locationOptions
        systemOptions: root.systemOptions
        assetOptions: root.assetOptions
        componentOptions: root.componentOptions
        sourceTypeOptions: root.sourceTypeOptions
        sourceWorkRequestOptions: root.sourceWorkRequestOptions
        workOrderTypeOptions: root.workOrderTypeOptions
        priorityOptions: root.priorityOptions
        vendorOptions: root.vendorOptions

        onSubmitted: function(payload) {
            if (editorDialog.modeTitle === "Create Work Order") {
                root.createRequested(payload)
            } else {
                root.updateRequested(payload)
            }
            editorDialog.close()
        }
    }

    MaintenanceDialogs.WorkOrderStatusDialog {
        id: statusDialog
        objectName: "workOrderStatusDialog"

        statusOptions: root.statusOptions

        onSubmitted: function(statusValue) {
            const state = statusDialog.workOrderData && statusDialog.workOrderData.state
                ? statusDialog.workOrderData.state
                : (statusDialog.workOrderData || {})
            root.statusChangeRequested(
                String(state.workOrderId || ""),
                String(statusValue || ""),
                Number(state.expectedVersion || 0)
            )
            statusDialog.close()
        }
    }
}

