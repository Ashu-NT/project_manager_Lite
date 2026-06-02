pragma ComponentBehavior: Bound

import QtQuick
import "WorkOrdersColumnConfig.js" as ColumnConfig

Item {
    id: root

    property var maintenanceCatalog: null
    property var platformCatalog: null
    property var workspaceController: null

    readonly property string tableId: "maintenance.work_orders.table"

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "maintenance_management.work_orders",
            "title": "Work Orders",
            "summary": "Execution planning, lifecycle control, and assignment readiness for maintenance delivery."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var workOrdersModel: root.workspaceController
        ? root.workspaceController.workOrders
        : ({
            "title": "Work Orders",
            "subtitle": "Review execution records, readiness state, and lifecycle progression.",
            "emptyState": "Maintenance work-orders desktop API is not connected in this QML preview.",
            "items": []
        })

    readonly property var selectedWorkOrderModel: root.workspaceController
        ? root.workspaceController.selectedWorkOrder
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a work order to inspect execution scope, planning state, and update actions.",
            "fields": [],
            "state": {}
        })

    readonly property var tableColumns: ColumnConfig.baseColumns()

    property var columns: []

    function initializeColumns() {
        root.columns = ColumnConfig.baseColumns()
    }

    Component.onCompleted: { root.initializeColumns() }
}
