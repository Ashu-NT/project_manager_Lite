import QtQuick
import App.Mock 1.0 as AppMock
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var stockSignalsModel: AppMock.MockFactory.catalog("Stock Status Signals")
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
