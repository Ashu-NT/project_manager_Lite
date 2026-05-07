import QtQuick
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var itemsModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedInventoryItemId: ""
    property bool isBusy: false

    signal inventoryItemSelected(string itemId)
    signal editRequested(var itemData)
    signal toggleRequested(var itemData)

    title: root.itemsModel.title || "Item Catalog"
    subtitle: root.itemsModel.subtitle || ""
    emptyState: root.itemsModel.emptyState || ""
    items: root.itemsModel.items || []
    selectedItemId: root.selectedInventoryItemId
    primaryActionLabel: "Edit"
    secondaryActionLabel: "Toggle Active"
    actionsEnabled: !root.isBusy

    onItemSelected: function(itemId) {
        root.inventoryItemSelected(itemId)
    }

    onPrimaryActionRequested: function(itemData) {
        root.editRequested(itemData)
    }

    onSecondaryActionRequested: function(itemData) {
        root.toggleRequested(itemData)
    }
}
