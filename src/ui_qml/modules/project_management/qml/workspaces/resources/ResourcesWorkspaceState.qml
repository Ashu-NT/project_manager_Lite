pragma ComponentBehavior: Bound

import QtQuick
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "ResourcesColumnConfig.js" as ColumnConfig

Item {
    id: root

    // ── Injected dependencies ────────────────────────────────────────────
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog: null
    property var workspaceController: null

    // ── Column table ID ──────────────────────────────────────────────────
    readonly property string tableId: "pm.resources.table"

    // ── Readonly derived properties ──────────────────────────────────────
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.resources",
            "title": "Resources",
            "summary": "Resource capacity, allocation, project assignments, and utilization views."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var resourcesModel: root.workspaceController
        ? root.workspaceController.resources
        : ({
            "title": "Resource Pool",
            "subtitle": "Manage capacity, worker types, and resource availability.",
            "emptyState": "Project-management resources desktop API is not connected in this QML preview.",
            "items": []
        })

    readonly property var selectedResourceModel: root.workspaceController
        ? root.workspaceController.selectedResource
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a resource from the pool to review details or edit its setup.",
            "fields": [],
            "state": {}
        })

    // ── Detail sections ──────────────────────────────────────────────────
    readonly property var detailSections: [
        "Overview", "Assignments", "Capacity", "Calendar",
        "Skills", "Certifications", "Cost Rates", "Availability", "Activity"
    ]

    // ── Detail actions ───────────────────────────────────────────────────
    function detailActionsForSection(sectionIndex, selectionContext) {
        const sectionName = detailSections[sectionIndex] || ""
        const selection = selectionContext || {}
        if (sectionName === "Overview") {
            const state = root.selectedResourceModel
                ? (root.selectedResourceModel.state || {}) : {}
            const isActive = state.isActive !== false
            return [
                { "id": "edit",   "label": "Edit",
                  "icon": "edit",    "enabled": true, "danger": false },
                { "id": "toggle", "label": isActive ? "Deactivate" : "Activate",
                  "icon": isActive ? "close" : "approve", "enabled": true, "danger": false },
                { "id": "delete", "label": "Delete",
                  "icon": "delete",  "enabled": true, "danger": true  }
            ]
        }
        if (sectionName === "Skills" && String(selection.selectedSkillId || "").length > 0) {
            return [
                { "id": "remove_skill", "label": "Remove", "icon": "delete", "enabled": true, "danger": true }
            ]
        }
        if (sectionName === "Certifications" && String(selection.selectedCertificationId || "").length > 0) {
            return [
                { "id": "remove_certification", "label": "Remove", "icon": "delete", "enabled": true, "danger": true }
            ]
        }
        return []
    }

    // ── Column configuration ─────────────────────────────────────────────
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
                root.tableId,
                ColumnConfig.buildColumnState(newColumns)
            )
        }
        root.columns = newColumns
    }

    // ── Helper functions ─────────────────────────────────────────────────
    function categoryIndexForValue(v) {
        const opts = root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
        for (let i = 0; i < opts.length; i++) {
            if (String(opts[i].value || "") === String(v || "")) return i
        }
        return 0
    }

    // ── Initialization ───────────────────────────────────────────────────
    Component.onCompleted: {
        root.initializeColumns()
    }
}
