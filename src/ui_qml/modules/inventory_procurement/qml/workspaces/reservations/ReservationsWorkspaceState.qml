pragma ComponentBehavior: Bound

import QtQuick
import "ReservationsColumnConfig.js" as ColumnConfig

Item {
    id: root

    property var inventoryCatalog: null
    property var platformCatalog: null
    property var workspaceController: null

    readonly property string tableId: "inventory.reservations.table"

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "inventory_procurement.reservations",
            "title": "Reservations",
            "summary": "Material reservations, fulfillment, and stock allocation management."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var reservationsModel: root.workspaceController
        ? root.workspaceController.reservations
        : ({
            "title": "Reservations",
            "subtitle": "Track material reservations and fulfillment status.",
            "emptyState": "Inventory reservations desktop API is not connected in this QML preview.",
            "items": []
        })

    readonly property var selectedReservationModel: root.workspaceController
        ? root.workspaceController.selectedReservation
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a reservation to review its details and fulfillment state.",
            "fields": [],
            "state": {}
        })

    readonly property var detailSections: ["Details", "Documents", "Activity"]

    property var columns: []

    function initializeColumns() {
        root.columns = ColumnConfig.baseColumns()
    }

    Component.onCompleted: { root.initializeColumns() }
}
