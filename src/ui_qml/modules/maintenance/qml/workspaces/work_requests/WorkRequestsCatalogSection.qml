import QtQuick
import Maintenance.Widgets 1.0 as MaintenanceWidgets

MaintenanceWidgets.RecordListCard {
    id: root

    property var workRequestsModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedWorkRequestId: ""
    property bool isBusy: false

    signal workRequestSelected(string workRequestId)
    signal editRequested(var workRequestData)
    signal statusRequested(var workRequestData)

    title: root.workRequestsModel.title || "Work Requests"
    subtitle: root.workRequestsModel.subtitle || ""
    emptyState: root.workRequestsModel.emptyState || ""
    items: root.workRequestsModel.items || []
    selectedItemId: root.selectedWorkRequestId
    primaryActionLabel: "Edit"
    secondaryActionLabel: "Status"
    actionsEnabled: !root.isBusy

    onItemSelected: function(workRequestId) {
        root.workRequestSelected(workRequestId)
    }

    onPrimaryActionRequested: function(workRequestData) {
        root.editRequested(workRequestData)
    }

    onSecondaryActionRequested: function(workRequestData) {
        root.statusRequested(workRequestData)
    }
}
