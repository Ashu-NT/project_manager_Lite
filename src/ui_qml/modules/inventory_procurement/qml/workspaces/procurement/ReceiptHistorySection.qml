import QtQuick
import App.Mock 1.0 as AppMock
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var receiptsModel: AppMock.MockFactory.catalog()

    title: root.receiptsModel.title || "Receipt History"
    subtitle: root.receiptsModel.subtitle || ""
    emptyState: root.receiptsModel.emptyState || ""
    items: root.receiptsModel.items || []
}
