pragma ComponentBehavior: Bound

import QtQuick
import Maintenance.Controllers 1.0 as MaintenanceControllers

Item {
    id: root

    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    property var workspaceController: null

    readonly property string tableId: "maintenance.preventive.table"

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "maintenance_management.preventive",
            "title": "Preventive Maintenance",
            "summary": "Preventive maintenance plans, templates, and scheduled queue management."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var selectedPlanModel: root.workspaceController
        ? root.workspaceController.selectedPlan
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a preventive maintenance plan to review details and schedule.",
            "fields": [],
            "state": {}
        })

    readonly property var detailSections: ["Details", "Tasks", "Schedule", "Activity"]
}
