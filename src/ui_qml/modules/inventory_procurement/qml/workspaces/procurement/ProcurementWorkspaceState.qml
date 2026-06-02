pragma ComponentBehavior: Bound

import QtQuick
import "ProcurementColumnConfig.js" as ColumnConfig

Item {
    id: root

    property var inventoryCatalog: null
    property var platformCatalog: null
    property var workspaceController: null

    readonly property string tableId: "inventory.procurement.requisitions.table"
    readonly property string poTableId: "inventory.procurement.orders.table"

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "inventory_procurement.procurement",
            "title": "Procurement",
            "summary": "Purchase requisitions, purchase orders, and receiving workflows."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var requisitionsModel: root.workspaceController
        ? root.workspaceController.requisitions
        : ({
            "title": "Purchase Requisitions",
            "subtitle": "Manage purchase requisitions through approval and conversion.",
            "emptyState": "No requisitions found.",
            "items": []
        })

    readonly property var selectedRequisitionModel: root.workspaceController
        ? root.workspaceController.selectedRequisition
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a requisition to review details and lines.",
            "fields": [],
            "state": {}
        })

    readonly property var detailSections: ["Details", "Lines", "Receipts", "Documents", "Activity"]

    property var columns: []

    function initializeColumns() {
        root.columns = ColumnConfig.baseRequisitionColumns()
    }

    Component.onCompleted: { root.initializeColumns() }
}
