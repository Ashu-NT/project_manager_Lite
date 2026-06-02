pragma ComponentBehavior: Bound

import QtQuick
import "ProjectsColumnConfig.js" as ColumnConfig

Item {
    id: root

    // ── Injected dependencies ────────────────────────────────────────────
    property var pmCatalog: null
    property var workspaceController: null

    // ── Column table ID ──────────────────────────────────────────────────
    readonly property string tableId: "pm.projects.table"

    // ── Readonly derived properties ──────────────────────────────────────
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.projects",
            "title": "Projects",
            "summary": "Project lifecycle, ownership, status, and project list workflows."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var projectsModel: root.workspaceController
        ? root.workspaceController.projects
        : ({
            "title": "Project Catalog",
            "subtitle": "Create, edit, and review project lifecycle records.",
            "emptyState": "Project-management projects desktop API is not connected in this QML preview.",
            "items": []
        })

    readonly property var selectedProjectModel: root.workspaceController
        ? root.workspaceController.selectedProject
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a project from the catalog to review details or edit its setup.",
            "fields": [],
            "state": {}
        })

    readonly property var projectTasksModel: root.workspaceController
        ? root.workspaceController.projectTasks
        : ({ "title": "Tasks", "subtitle": "", "emptyState": "Open this section to load project tasks.", "items": [] })

    readonly property var projectResourcesModel: root.workspaceController
        ? root.workspaceController.projectResources
        : ({ "title": "Resources", "subtitle": "", "emptyState": "Open this section to load project resources.", "items": [] })

    // ── RBAC & Capabilities ──────────────────────────────────────────────
    readonly property bool hasInvCap: root.pmCatalog
        ? root.pmCatalog.hasCapability("inventory.reservations.create")
        : false

    readonly property bool hasProcCap: root.pmCatalog
        ? root.pmCatalog.hasCapability("procurement.purchase_orders.read")
        : false

    // ── Detail sections ──────────────────────────────────────────────────
    readonly property var detailSections: {
        const secs = ["Overview", "Schedule", "Tasks", "Resources", "Financials", "Risks"]
        if (root.hasInvCap)  secs.push("Material Demand")
        if (root.hasProcCap) secs.push("Procurement")
        secs.push("Documents")
        secs.push("Activity")
        return secs
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

    // ── Bulk change properties ───────────────────────────────────────────
    readonly property var bulkChangeProperties: {
        const props = []
        const statusOptions = root.workspaceController
            ? (root.workspaceController.bulkStatusOptions || [])
            : []
        if (statusOptions.length > 0) {
            props.push({ "id": "status", "label": "Status", "values": statusOptions })
        }
        return props
    }

    // ── Helper functions ─────────────────────────────────────────────────
    function statusIndexForValue(statusValue) {
        const opts = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
        for (let i = 0; i < opts.length; i++) {
            if (String(opts[i].value || "") === String(statusValue || "")) return i
        }
        return 0
    }

    function lazyLoadDetailSection(detailPage, sectionIndex) {
        if (root.workspaceController === null) return
        const secName = root.detailSections[sectionIndex] || ""
        if      (secName === "Tasks")     root.workspaceController.loadProjectTasks()
        else if (secName === "Resources") root.workspaceController.loadProjectResources()
        else if (secName === "Financials") root.workspaceController.loadProjectFinancials()
        else if (secName === "Risks")     root.workspaceController.loadProjectRisks()
        else if (secName === "Documents") root.workspaceController.loadProjectDocuments()
        else if (secName === "Activity")  root.workspaceController.loadProjectActivity()
    }

    // ── Initialization ───────────────────────────────────────────────────
    Component.onCompleted: {
        root.initializeColumns()
    }
}
