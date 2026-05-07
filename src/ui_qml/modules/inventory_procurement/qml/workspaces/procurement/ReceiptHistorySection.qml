import QtQuick
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var receiptsModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })

    title: root.receiptsModel.title || "Receipt History"
    subtitle: root.receiptsModel.subtitle || ""
    emptyState: root.receiptsModel.emptyState || ""
    items: root.receiptsModel.items || []
}
