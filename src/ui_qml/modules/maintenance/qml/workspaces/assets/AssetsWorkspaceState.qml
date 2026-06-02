pragma ComponentBehavior: Bound

import QtQuick

Item {
    id: root

    property var maintenanceCatalog: null
    property var workspaceController: null

    readonly property string tableId: "maintenance.assets.table"

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "maintenance_management.assets",
            "title": "Asset Library",
            "summary": "Locations, systems, assets, and components — full asset hierarchy management."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var selectedAssetModel: root.workspaceController
        ? root.workspaceController.selectedAsset
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select an asset to review its details, work history, and specifications.",
            "fields": [],
            "state": {}
        })

    readonly property var detailSections: ["Details", "Work History", "Specifications", "Documents", "Activity"]
}
