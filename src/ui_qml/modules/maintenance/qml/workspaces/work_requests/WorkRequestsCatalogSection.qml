import QtQuick
import App.Mock 1.0 as AppMock
import Maintenance.Widgets 1.0 as MaintenanceWidgets

MaintenanceWidgets.RecordListCard {
    id: root

    property var workRequestsModel: AppMock.MockFactory.catalog()
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
    primaryActionIcon: "edit"
    secondaryActionLabel: "Status"
    secondaryActionIcon: "workflow"
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
