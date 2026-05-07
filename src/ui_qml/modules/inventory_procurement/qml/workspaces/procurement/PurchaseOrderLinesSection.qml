import QtQuick
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var lineModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })

    title: root.lineModel.title || "Purchase-Order Lines"
    subtitle: root.lineModel.subtitle || ""
    emptyState: root.lineModel.emptyState || ""
    items: root.lineModel.items || []
}
