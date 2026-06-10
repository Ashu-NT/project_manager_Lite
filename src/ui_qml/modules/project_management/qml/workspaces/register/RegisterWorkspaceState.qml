pragma ComponentBehavior: Bound

import QtQuick
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "RegisterColumnConfig.js" as ColumnConfig

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog: null
    property var workspaceController: null

    readonly property string tableId: "pm.register.table"

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.register",
            "title": "Register",
            "summary": "Risk register, issues log, and change management across projects."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var registerModel: root.workspaceController
        ? root.workspaceController.registerEntries
        : ({
            "title": "Risk & Issue Register",
            "subtitle": "Track risks, issues, and change requests across all projects.",
            "emptyState": "Project-management register desktop API is not connected in this QML preview.",
            "items": []
        })

    readonly property var selectedEntryModel: root.workspaceController
        ? root.workspaceController.selectedEntry
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a register entry to review its details and response plan.",
            "fields": [],
            "state": {}
        })

    readonly property var detailSections: ["Details", "Impact", "Response", "Links"]

    readonly property var detailActions: {
        return [
            { "id": "edit",   "label": "Edit",   "icon": "edit",   "enabled": true, "danger": false },
            { "id": "delete", "label": "Delete", "icon": "delete", "enabled": true, "danger": true  }
        ]
    }

    property var columns: []

    function initializeColumns() {
        const base = ColumnConfig.baseColumns()
        if (root.workspaceController !== null) {
            const saved = root.workspaceController.loadTableColumnState(root.tableId)
            root.columns = ColumnConfig.applyColumnState(base, saved)
        } else {
            root.columns = base
        }
    }

    function saveColumnState(newColumns) {
        if (root.workspaceController !== null) {
            root.workspaceController.saveTableColumnState(
                root.tableId, ColumnConfig.buildColumnState(newColumns))
        }
        root.columns = newColumns
    }

    readonly property var bulkChangeProperties: {
        const props = []
        const statusOptions = root.workspaceController
            ? (root.workspaceController.bulkStatusOptions || []) : []
        if (statusOptions.length > 0)
            props.push({ "id": "status", "label": "Status", "values": statusOptions })
        return props
    }

    function optionIndexForValue(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    Component.onCompleted: { root.initializeColumns() }
}
