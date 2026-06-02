pragma ComponentBehavior: Bound

import QtQuick
import "CatalogColumnConfig.js" as ColumnConfig

Item {
    id: root

    property var inventoryCatalog: null
    property var workspaceController: null

    readonly property string tableId: "inventory.catalog.items.table"
    readonly property string categoriesTableId: "inventory.catalog.categories.table"

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "inventory_procurement.catalog",
            "title": "Catalog",
            "summary": "Item catalog management, categories, and item specifications."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var itemsModel: root.workspaceController
        ? root.workspaceController.items
        : ({
            "title": "Items",
            "subtitle": "Manage catalog items, specifications, and stock parameters.",
            "emptyState": "Inventory catalog desktop API is not connected in this QML preview.",
            "items": []
        })

    readonly property var categoriesModel: root.workspaceController
        ? root.workspaceController.categories
        : ({
            "title": "Categories",
            "subtitle": "Manage item categories and classification.",
            "emptyState": "No categories found.",
            "items": []
        })

    readonly property var selectedItemModel: root.workspaceController
        ? root.workspaceController.selectedItem
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select an item to review details, specifications, and stock parameters.",
            "fields": [],
            "state": {}
        })

    readonly property var detailSections: ["Details", "Stock", "Pricing", "Documents", "Activity"]

    property var columns: []

    function initializeColumns() {
        root.columns = ColumnConfig.baseItemColumns()
    }

    Component.onCompleted: { root.initializeColumns() }
}
