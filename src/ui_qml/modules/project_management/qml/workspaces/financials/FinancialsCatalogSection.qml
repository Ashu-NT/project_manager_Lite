import QtQuick
import App.Mock 1.0 as AppMock
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

ProjectManagementWidgets.RecordListCard {
    id: root

    property var costsModel: AppMock.MockFactory.catalog()
    property string selectedCostId: ""
    property bool isBusy: false

    signal costSelected(string costId)
    signal editRequested(var costData)
    signal deleteRequested(var costData)

    title: root.costsModel.title || "Cost Items"
    subtitle: root.costsModel.subtitle || ""
    emptyState: root.costsModel.emptyState || ""
    items: root.costsModel.items || []
    selectedItemId: root.selectedCostId
    primaryActionLabel: "Edit"
    secondaryActionLabel: "Delete"
    secondaryDanger: true
    actionsEnabled: !root.isBusy

    onItemSelected: function(itemId) {
        root.costSelected(itemId)
    }

    onPrimaryActionRequested: function(itemData) {
        root.editRequested(itemData)
    }

    onSecondaryActionRequested: function(itemData) {
        root.deleteRequested(itemData)
    }
}
