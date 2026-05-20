import QtQuick
import App.Mock 1.0 as AppMock
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var transactionsModel: AppMock.MockFactory.catalog()

    title: root.transactionsModel.title || "Recent Movements"
    subtitle: root.transactionsModel.subtitle || ""
    emptyState: root.transactionsModel.emptyState || ""
    items: root.transactionsModel.items || []
    selectedItemId: ""
    primaryActionLabel: ""
    secondaryActionLabel: ""
    tertiaryActionLabel: ""
    actionsEnabled: false
}
