import QtQuick
import Maintenance.Widgets 1.0 as MaintenanceWidgets

MaintenanceWidgets.RecordListCard {
    id: root

    property var catalogModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property bool isBusy: false

    signal itemChosen(string itemId)
    signal primaryActionChosen(var itemData)
    signal secondaryActionChosen(var itemData)

    title: root.catalogModel.title || ""
    subtitle: root.catalogModel.subtitle || ""
    emptyState: root.catalogModel.emptyState || ""
    items: root.catalogModel.items || []
    primaryActionLabel: "Edit"
    secondaryActionLabel: "Toggle Active"
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
