import QtQuick
import App.Mock 1.0 as AppMock
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var requisitionsModel: AppMock.MockFactory.catalog()
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
