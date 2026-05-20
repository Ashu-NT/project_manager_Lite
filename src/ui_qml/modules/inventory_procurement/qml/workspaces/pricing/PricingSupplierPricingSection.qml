import QtQuick
import App.Mock 1.0 as AppMock
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var supplierPricingModel: AppMock.MockFactory.catalog("Supplier Price Lines")
    property bool isBusy: false

    title: root.supplierPricingModel.title || "Supplier Price Lines"
    subtitle: root.supplierPricingModel.subtitle || ""
    emptyState: root.supplierPricingModel.emptyState || ""
    items: root.supplierPricingModel.items || []
    actionsEnabled: !root.isBusy
    primaryActionLabel: ""
    secondaryActionLabel: ""
    tertiaryActionLabel: ""
}
