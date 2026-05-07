import QtQuick
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var balancesModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedBalanceId: ""
    property bool isBusy: false

    signal balanceSelected(string balanceId)
    signal issueRequested(var balanceData)
    signal adjustmentRequested(var balanceData)
    signal transferRequested(var balanceData)

    title: root.balancesModel.title || "Stock Balances"
    subtitle: root.balancesModel.subtitle || ""
    emptyState: root.balancesModel.emptyState || ""
    items: root.balancesModel.items || []
    selectedItemId: root.selectedBalanceId
    primaryActionLabel: "Issue"
    secondaryActionLabel: "Adjust"
    tertiaryActionLabel: "Transfer"
    actionsEnabled: !root.isBusy

    onItemSelected: function(balanceId) {
        root.balanceSelected(balanceId)
    }

    onPrimaryActionRequested: function(balanceData) {
        root.issueRequested(balanceData)
    }

    onSecondaryActionRequested: function(balanceData) {
        root.adjustmentRequested(balanceData)
    }

    onTertiaryActionRequested: function(balanceData) {
        root.transferRequested(balanceData)
    }
}
