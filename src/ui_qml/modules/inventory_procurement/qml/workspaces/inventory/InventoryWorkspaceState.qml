pragma ComponentBehavior: Bound

import QtQuick
import "InventoryColumnConfig.js" as ColumnConfig

Item {
    id: root

    property var inventoryCatalog: null
    property var workspaceController: null

    readonly property string tableId: "inventory.stock.table"

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "inventory_procurement.inventory",
            "title": "Inventory",
            "summary": "Stock levels, location management, and inventory adjustments."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var stockItemsModel: root.workspaceController
        ? root.workspaceController.stockItems
        : ({
            "title": "Stock",
            "subtitle": "Current stock levels by item and location.",
            "emptyState": "Inventory stock desktop API is not connected in this QML preview.",
            "items": []
        })

    readonly property var selectedStockItemModel: root.workspaceController
        ? root.workspaceController.selectedStockItem
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a stock item to review quantities, movements, and adjustments.",
            "fields": [],
            "state": {}
        })

    readonly property var detailSections: ["Details", "Movements", "Reservations", "Activity"]

    property var columns: []

    function initializeColumns() {
        root.columns = ColumnConfig.baseColumns()
    }

    Component.onCompleted: { root.initializeColumns() }
}
