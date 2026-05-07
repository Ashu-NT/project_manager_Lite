import QtQuick
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var requisitionsModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedRequisitionId: ""

    signal requisitionSelected(string requisitionId)

    title: root.requisitionsModel.title || "Requisitions"
    subtitle: root.requisitionsModel.subtitle || ""
    emptyState: root.requisitionsModel.emptyState || ""
    items: root.requisitionsModel.items || []
    selectedItemId: root.selectedRequisitionId

    onItemSelected: function(requisitionId) {
        root.requisitionSelected(requisitionId)
    }
}
