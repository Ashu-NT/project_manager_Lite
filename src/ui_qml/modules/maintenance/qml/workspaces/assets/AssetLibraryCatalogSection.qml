import QtQuick
import App.Mock 1.0 as AppMock
import Maintenance.Widgets 1.0 as MaintenanceWidgets

MaintenanceWidgets.RecordListCard {
    id: root

    property var catalogModel: AppMock.MockFactory.catalog()
    property bool isBusy: false

    signal itemChosen(string itemId)
    signal primaryActionChosen(var itemData)
    signal secondaryActionChosen(var itemData)

    title: root.catalogModel.title || ""
    subtitle: root.catalogModel.subtitle || ""
    emptyState: root.catalogModel.emptyState || ""
    items: root.catalogModel.items || []
    primaryActionLabel: "Edit"
    primaryActionIcon: "edit"
    secondaryActionLabel: "Toggle Active"
    secondaryActionIcon: "workflow"
    actionsEnabled: !root.isBusy

    onItemSelected: function(itemId) {
        root.itemChosen(itemId)
    }

    onPrimaryActionRequested: function(itemData) {
        root.primaryActionChosen(itemData)
    }

    onSecondaryActionRequested: function(itemData) {
        root.secondaryActionChosen(itemData)
    }
}
