pragma ComponentBehavior: Bound

import QtQuick
import App.Mock 1.0 as AppMock
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "TasksColumnConfig.js" as ColumnConfig

Item {
    id: root

    // ── Injected dependencies ────────────────────────────────────────────
    property var shellModel: null
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog: null
    property var workspaceController: null

    // ── Column table ID ──────────────────────────────────────────────────
    readonly property string tableId: "pm.tasks.table"

    // ── Readonly derived properties ──────────────────────────────────────
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.tasks",
            "title": "Tasks",
            "summary": "Task planning, progress, dependencies, assignments, and execution state."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var tasksModel: root.workspaceController
        ? root.workspaceController.tasks
        : ({
            "title": "Task Catalog",
            "subtitle": "Edit delivery tasks, progress, and execution priorities.",
            "emptyState": "Project-management tasks desktop API is not connected in this QML preview.",
            "items": []
        })

    readonly property var tasksTableModel: root.workspaceController
        ? root.workspaceController.tasksTableModel
        : null

    readonly property var selectedTaskModel: root.workspaceController
        ? root.workspaceController.selectedTask
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a task from the catalog to review details or update progress.",
            "fields": [],
            "state": {}
        })

    readonly property var assignmentsModel: root.workspaceController
        ? root.workspaceController.assignments
        : ({
            "title": "Assignments",
            "subtitle": "Resource allocations and logged effort for this task.",
            "emptyState": "Select a task to review assignments and effort coverage.",
            "items": []
        })

    readonly property var dependenciesModel: root.workspaceController
        ? root.workspaceController.dependencies
        : ({
            "title": "Dependencies",
            "subtitle": "Sequencing links and lag settings for this task.",
            "emptyState": "Select a task to review predecessor and successor links.",
            "items": []
        })

    readonly property var timeAssignmentSummaryModel: root.workspaceController
        ? root.workspaceController.timeAssignmentSummary
        : ({
            "title": "",
            "subtitle": "",
            "emptyState": "Select a task assignment to review detailed time entries, period status, and labor totals.",
            "fields": [],
            "state": {}
        })

    readonly property var timeEntriesModel: root.workspaceController
        ? root.workspaceController.timeEntries
        : ({
            "title": "Time Entries",
            "subtitle": "Detailed labor entries for the selected task assignment.",
            "emptyState": "Select a task assignment to review or capture labor entries.",
            "items": []
        })

    readonly property var selectedTimeEntryModel: root.workspaceController
        ? root.workspaceController.selectedTimeEntry
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select an entry from the period list to review or edit its captured labor note.",
            "fields": [],
            "state": {}
        })

    readonly property var collaborationCommentsModel: root.workspaceController
        ? root.workspaceController.collaborationComments
        : ({
            "title": "Task Collaboration",
            "subtitle": "Comments, mentions, attachments, and linked shared documents for the selected task.",
            "emptyState": "Select a task to review collaboration updates and post comments.",
            "items": []
        })

    readonly property var collaborationPresenceModel: root.workspaceController
        ? root.workspaceController.collaborationPresence
        : ({
            "title": "Active Presence",
            "subtitle": "People currently reviewing or updating the selected task.",
            "emptyState": "Select a task to review active collaboration presence.",
            "items": []
        })

    readonly property var skillRequirementsModel: root.workspaceController
        ? root.workspaceController.taskSkillRequirements
        : ({
            "title": "Skill Requirements",
            "subtitle": "Skill and certification requirements for resource assignment.",
            "emptyState": "Select a task to review skill and certification requirements.",
            "items": []
        })

    readonly property var scheduleImpactModel: root.workspaceController
        ? root.workspaceController.scheduleImpact
        : ({
            "available": false,
            "taskId": "",
            "summary": "Select a task to view schedule impact analysis.",
            "rows": [],
            "affectedCount": 0,
            "maxProjectFinishShiftDays": 0,
            "requiresApproval": false,
            "approvalLabel": "",
            "newlyCriticalCount": 0,
            "noLongerCriticalCount": 0
        })

    // ── Pagination state ─────────────────────────────────────────────────
    readonly property int currentPage: root.workspaceController
        ? root.workspaceController.taskPage
        : 1

    readonly property int pageSize: root.workspaceController
        ? root.workspaceController.taskPageSize
        : 25

    readonly property int totalItems: root.workspaceController
        ? root.workspaceController.taskTotalCount
        : 0

    // ── RBAC & Capabilities ──────────────────────────────────────────────
    readonly property bool hasInvStockCapability: root.pmCatalog
        ? root.pmCatalog.hasCapability("inventory.stock.read")
        : false

    readonly property bool hasInvReservationsCapability: root.pmCatalog
        ? root.pmCatalog.hasCapability("inventory.reservations.create")
        : false

    readonly property bool hasProcurementCapability: root.pmCatalog
        ? root.pmCatalog.hasCapability("procurement.requisitions.create")
        : false

    // ── Column configuration ─────────────────────────────────────────────
    property var columns: []

    function initializeColumns() {
        const base = ColumnConfig.baseColumns(root.hasInvStockCapability)
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

    // ── Detail sections list ─────────────────────────────────────────────
    readonly property var detailSections: {
        const secs = ["Details", "Assignments", "Skills", "Dependencies", "Time"]
        if (root.hasInvStockCapability)       secs.push("Material Demand")
        if (root.hasInvReservationsCapability) secs.push("Reservations")
        if (root.hasProcurementCapability)    secs.push("Procurement")
        secs.push("Schedule Impact")
        secs.push("Activity")
        return secs
    }

    // ── Detail page actions (section-aware) ───────────────────────────────
    function detailActionsForSection(sectionIndex) {
        const sectionName = detailSections[sectionIndex] || ""
        if (sectionName === "Details") {
            const actions = [
                { "id": "edit",     "label": "Edit",     "icon": "edit",    "enabled": true, "danger": false },
                { "id": "progress", "label": "Progress", "icon": "approve", "enabled": true, "danger": false },
                { "id": "delete",   "label": "Delete",   "icon": "delete",  "enabled": true, "danger": true  }
            ]
            if (root.hasInvReservationsCapability) {
                actions.splice(2, 0, {
                    "id": "reserve_material",
                    "label": "Reserve Material",
                    "icon": "storage",
                    "enabled": root.selectedTaskModel && root.selectedTaskModel.id ? true : false,
                    "danger": false
                })
            }
            return actions
        }
        return []
    }

    // ── Bulk change properties ───────────────────────────────────────────
    readonly property var bulkChangeProperties: {
        const properties = []
        const statusOptions = root.workspaceController
            ? (root.workspaceController.bulkStatusOptions || [])
            : []
        if (statusOptions.length > 0) {
            properties.push({
                "id": "status",
                "label": "Status",
                "values": statusOptions
            })
        }
        return properties
    }

    // ── Helper: option index lookup ──────────────────────────────────────
    function optionIndexForValue(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) {
                return i
            }
        }
        return 0
    }

    // ── Navigation helpers ───────────────────────────────────────────────
    function navigateToRoute(routeId) {
        if (root.shellModel && String(routeId || "").length > 0) {
            root.shellModel.selectRoute(String(routeId || ""))
        }
    }

    function openTaskReservationsRoute() {
        root.navigateToRoute("inventory_procurement.reservations")
    }

    function openTaskProcurementRoute() {
        root.navigateToRoute("inventory_procurement.procurement")
    }

    // ── Detail opening helpers ───────────────────────────────────────────
    function canViewDetailSection(sectionName) {
        if (sectionName === "Material Demand") return root.hasInvStockCapability
        if (sectionName === "Reservations") return root.hasInvReservationsCapability
        if (sectionName === "Procurement") return root.hasProcurementCapability
        return true
    }

    function lazyLoadDetailSection(detailPage, sectionIndex) {
        if (root.workspaceController === null) return
        const page = detailPage
        const entry = page ? (page.sections[sectionIndex] || "") : ""
        const label = (typeof entry === "string") ? entry : (entry.label || "")

        if      (label === "Assignments")     root.workspaceController.loadSelectedTaskAssignments()
        else if (label === "Skills")          root.workspaceController.loadSelectedTaskSkillRequirements()
        else if (label === "Dependencies")    root.workspaceController.loadSelectedTaskDependencies()
        else if (label === "Time")            root.workspaceController.loadSelectedTaskTime()
        else if (label === "Schedule Impact") root.workspaceController.loadSelectedTaskScheduleImpact()
        else if (label === "Activity")        root.workspaceController.loadSelectedTaskCollaboration()
    }

    // ── Initialization ───────────────────────────────────────────────────
    Component.onCompleted: {
        root.initializeColumns()
    }
}
