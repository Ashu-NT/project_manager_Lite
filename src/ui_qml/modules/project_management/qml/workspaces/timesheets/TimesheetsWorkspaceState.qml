pragma ComponentBehavior: Bound

import QtQuick
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "TimesheetsColumnConfig.js" as ColumnConfig

Item {
    id: root

    // ── Injected dependencies ────────────────────────────────────────────
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog: null
    property var workspaceController: null

    // ── Column table ID ──────────────────────────────────────────────────
    readonly property string tableId: "pm.timesheets.review.table"

    // ── Readonly derived properties ──────────────────────────────────────
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.timesheets",
            "title": "Timesheets",
            "summary": "Time entry, review, labor capture, and project time reporting."
        })

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    readonly property var reviewQueueModel: root.workspaceController
        ? root.workspaceController.reviewQueue
        : ({
            "title": "Review Queue",
            "subtitle": "Timesheet periods pending review and approval.",
            "emptyState": "No timesheet periods match the current filter.",
            "items": []
        })

    readonly property var selectedPeriodModel: root.workspaceController
        ? root.workspaceController.reviewDetail
        : ({
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a timesheet period to review entries and manage approval.",
            "fields": [],
            "state": {}
        })

    readonly property var entriesModel: root.workspaceController
        ? root.workspaceController.entries
        : ({
            "title": "Time Entries",
            "subtitle": "",
            "emptyState": "No time entries for the selected period.",
            "items": []
        })

    readonly property var selectedEntryModel: root.workspaceController
        ? root.workspaceController.selectedEntry
        : ({
            "title": "",
            "subtitle": "",
            "emptyState": "Select an entry to review its labor note and details.",
            "fields": [],
            "state": {}
        })

    // ── Detail sections ──────────────────────────────────────────────────
    readonly property var detailSections: [
        "Entries",
        "Approval History",
        "Labor Notes",
        "Audit Trail"
    ]

    // ── Detail actions ───────────────────────────────────────────────────
    readonly property var detailActions: {
        const st = root.selectedPeriodModel ? (root.selectedPeriodModel.state || {}) : {}
        const status = String(st.periodStatus || "").toUpperCase()
        const hasPeriod = Boolean(st.periodId)
        const hasStatus = status.length > 0
        return [
            { "id": "submit",  "label": "Submit",        "icon": "approve",
              "enabled": hasPeriod && (!hasStatus || status === "DRAFT" || status === "OPEN"), "danger": false },
            { "id": "approve", "label": "Approve",       "icon": "approve",
              "enabled": hasPeriod && (!hasStatus || status === "SUBMITTED"), "danger": false },
            { "id": "reject",  "label": "Reject",        "icon": "close",
              "enabled": hasPeriod && (!hasStatus || status === "SUBMITTED"), "danger": true  },
            { "id": "lock",    "label": "Lock Period",   "icon": "lock",
              "enabled": hasPeriod && (!hasStatus || status === "APPROVED"), "danger": false },
            { "id": "unlock",  "label": "Unlock Period", "icon": "edit",
              "enabled": hasPeriod && (!hasStatus || status === "LOCKED"), "danger": false },
            { "id": "export",  "label": "Export",        "icon": "export", "enabled": true, "danger": false }
        ]
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
    function optionIndexForValue(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    // ── Initialization ───────────────────────────────────────────────────
    Component.onCompleted: {
        root.initializeColumns()
    }
}
