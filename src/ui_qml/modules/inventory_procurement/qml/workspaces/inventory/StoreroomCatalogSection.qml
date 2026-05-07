import QtQuick
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var storeroomsModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedStoreroomId: ""
    property bool isBusy: false

    signal storeroomSelected(string storeroomId)
    signal editRequested(var storeroomData)
    signal toggleRequested(var storeroomData)

    title: root.storeroomsModel.title || "Storerooms"
    subtitle: root.storeroomsModel.subtitle || ""
    emptyState: root.storeroomsModel.emptyState || ""
    items: root.storeroomsModel.items || []
    selectedItemId: root.selectedStoreroomId
    primaryActionLabel: "Edit"
    secondaryActionLabel: "Toggle Active"
    actionsEnabled: !root.isBusy

    onItemSelected: function(storeroomId) {
        root.storeroomSelected(storeroomId)
    }

    onPrimaryActionRequested: function(storeroomData) {
        root.editRequested(storeroomData)
    }

    onSecondaryActionRequested: function(storeroomData) {
        root.toggleRequested(storeroomData)
    }
}
