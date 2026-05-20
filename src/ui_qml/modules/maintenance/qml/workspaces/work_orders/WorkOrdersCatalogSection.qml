import QtQuick
import Maintenance.Widgets 1.0 as MaintenanceWidgets

MaintenanceWidgets.RecordListCard {
    id: root

    property var workOrdersModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedWorkOrderId: ""
    property bool isBusy: false

    signal workOrderSelected(string workOrderId)
    signal editRequested(var workOrderData)
    signal statusRequested(var workOrderData)

    title: root.workOrdersModel.title || "Work Orders"
    subtitle: root.workOrdersModel.subtitle || ""
    emptyState: root.workOrdersModel.emptyState || ""
    items: root.workOrdersModel.items || []
    selectedItemId: root.selectedWorkOrderId
    primaryActionLabel: "Edit"
    primaryActionIcon: "edit"
    secondaryActionLabel: "Status"
    secondaryActionIcon: "workflow"
    actionsEnabled: !root.isBusy

    onItemSelected: function(workOrderId) {
        root.workOrderSelected(workOrderId)
    }

    onPrimaryActionRequested: function(workOrderData) {
        root.editRequested(workOrderData)
    }

    onSecondaryActionRequested: function(workOrderData) {
        root.statusRequested(workOrderData)
    }
}
