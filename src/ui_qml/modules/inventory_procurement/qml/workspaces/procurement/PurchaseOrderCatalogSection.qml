import QtQuick
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var purchaseOrdersModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedPurchaseOrderId: ""

    signal purchaseOrderSelected(string purchaseOrderId)

    title: root.purchaseOrdersModel.title || "Purchase Orders"
    subtitle: root.purchaseOrdersModel.subtitle || ""
    emptyState: root.purchaseOrdersModel.emptyState || ""
    items: root.purchaseOrdersModel.items || []
    selectedItemId: root.selectedPurchaseOrderId

    onItemSelected: function(purchaseOrderId) {
        root.purchaseOrderSelected(purchaseOrderId)
    }
}
