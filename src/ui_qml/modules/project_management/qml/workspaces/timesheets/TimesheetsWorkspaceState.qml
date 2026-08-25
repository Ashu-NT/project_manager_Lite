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
            "title": "Review Queue",
            "summary": "Version-safe TimesheetPeriod review and decisions."
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
            "emptyState": "Select a timesheet period to inspect its decision context.",
            "fields": [],
            "state": {}
        })

    // ── Detail sections ──────────────────────────────────────────────────
    // ── Detail actions ───────────────────────────────────────────────────
    readonly property var detailActions: {
        const st = root.selectedPeriodModel ? (root.selectedPeriodModel.state || {}) : {}
        const actions = []
        if (st.canApprove === true)
            actions.push({ "id": "approve", "label": "Approve", "icon": "approve", "enabled": true, "danger": false })
        if (st.canReject === true)
            actions.push({ "id": "reject", "label": "Return", "icon": "close", "enabled": true, "danger": true })
        if (st.canLock === true)
            actions.push({ "id": "lock", "label": "Lock Period", "icon": "lock", "enabled": true, "danger": false })
        if (st.canUnlock === true)
            actions.push({ "id": "unlock", "label": "Unlock Period", "icon": "edit", "enabled": true, "danger": false })
        return actions
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
