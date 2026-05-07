import QtQuick
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var stockSignalsModel: ({
        "title": "Stock Status Signals",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property bool isBusy: false

    title: root.stockSignalsModel.title || "Stock Status Signals"
    subtitle: root.stockSignalsModel.subtitle || ""
    emptyState: root.stockSignalsModel.emptyState || ""
    items: root.stockSignalsModel.items || []
    actionsEnabled: !root.isBusy
    primaryActionLabel: ""
    secondaryActionLabel: ""
    tertiaryActionLabel: ""
}
