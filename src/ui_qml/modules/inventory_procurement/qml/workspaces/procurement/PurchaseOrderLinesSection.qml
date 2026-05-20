import QtQuick
import App.Mock 1.0 as AppMock
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var lineModel: AppMock.MockFactory.catalog()

    title: root.lineModel.title || "Purchase-Order Lines"
    subtitle: root.lineModel.subtitle || ""
    emptyState: root.lineModel.emptyState || ""
    items: root.lineModel.items || []
}
