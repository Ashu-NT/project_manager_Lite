pragma ComponentBehavior: Bound

import QtQuick
import "WorkRequestsColumnConfig.js" as ColumnConfig

Item {
    id: root

    property var maintenanceCatalog: null
    property var workspaceController: null

    readonly property string tableId: "maintenance.work_requests.table"

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "maintenance_management.work_requests",
            "title": "Work Requests",
            "summary": "Maintenance request intake, triage, and work order conversion."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var workRequestsModel: root.workspaceController
        ? root.workspaceController.workRequests
        : ({
            "title": "Work Requests",
            "subtitle": "Review and triage incoming maintenance requests.",
            "emptyState": "Maintenance work-requests desktop API is not connected in this QML preview.",
            "items": []
        })

    readonly property var selectedWorkRequestModel: root.workspaceController
        ? root.workspaceController.selectedWorkRequest
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a work request to review details and actions.",
            "fields": [],
            "state": {}
        })

    readonly property var detailSections: ["Details", "Activity"]

    property var columns: []

    function initializeColumns() {
        root.columns = ColumnConfig.baseColumns()
    }

    Component.onCompleted: { root.initializeColumns() }
}
