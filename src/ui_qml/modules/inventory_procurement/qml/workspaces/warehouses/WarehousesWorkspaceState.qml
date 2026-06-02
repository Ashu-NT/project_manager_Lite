pragma ComponentBehavior: Bound

import QtQuick

Item {
    id: root

    property var inventoryCatalog: null
    property var workspaceController: null

    readonly property string tableId: "inventory.warehouses.table"

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "inventory_procurement.warehouses",
            "title": "Warehouses & Locations",
            "summary": "Warehouse sites, storage locations, and location hierarchy management."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var warehousesModel: root.workspaceController
        ? root.workspaceController.warehouses
        : ({
            "title": "Warehouses",
            "subtitle": "Manage warehouse sites and storage zones.",
            "emptyState": "Inventory warehouses desktop API is not connected in this QML preview.",
            "items": []
        })

    readonly property var detailSections: ["Details", "Locations", "Stock", "Activity"]
}
