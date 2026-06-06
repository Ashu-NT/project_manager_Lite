pragma ComponentBehavior: Bound
import QtQuick
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    // ── Injected ──────────────────────────────────────────────────────────
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementSchedulingWorkspaceController workspaceController

    // ── Table ─────────────────────────────────────────────────────────────
    readonly property string activityTableId: "pm.scheduling.activity.table"
    property var activityColumns: []

    // ── UI state ──────────────────────────────────────────────────────────
    property string activePanelId: "activity_timeline"
    property string feedSearchText: ""
    property string selectedBaselineRegisterId: ""
    property bool detailOpen: false
    property int pendingDetailSection: 0

    // ── Panel tabs ────────────────────────────────────────────────────────
    readonly property var panelTabs: [
        { "id": "activity_timeline", "label": "Activity & Timeline" },
        { "id": "diagnostics",       "label": "Diagnostics"         },
        { "id": "resources",         "label": "Resources"           },
        { "id": "baselines",         "label": "Baselines"           },
        { "id": "delays",            "label": "Delays"              },
        { "id": "calendars",         "label": "Calendars"           },
        { "id": "activity_feed",     "label": "Activity Feed"       }
    ]

    // ── Computed ──────────────────────────────────────────────────────────
    readonly property string selectedBaselineRegisterStatus: {
        const rows = root.workspaceController ? (root.workspaceController.baselineRegisterRows || []) : []
        for (let i = 0; i < rows.length; i++) {
            if (String(rows[i].id || "") === root.selectedBaselineRegisterId)
                return String(rows[i].status || "").toLowerCase()
        }
        return ""
    }

    // ── Panel helpers ─────────────────────────────────────────────────────
    function panelIndex(panelId) {
        for (let i = 0; i < root.panelTabs.length; i++) {
            if (String(root.panelTabs[i].id || "") === String(panelId || "")) return i
        }
        return 0
    }

    function optionIndexForValue(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return list.length > 0 ? 0 : -1
    }

    function openActivityDetail(activityId) {
        if (root.workspaceController === null || !String(activityId || "").length) return
        root.workspaceController.activateActivity(String(activityId || ""))
        root.pendingDetailSection = 0
        root.detailOpen = true
    }

    // ── Column management ─────────────────────────────────────────────────
    function initColumns() {
        const base = _baseColumns()
        if (root.workspaceController !== null) {
            const saved = root.workspaceController.loadTableColumnState(root.activityTableId)
            root.activityColumns = _applyColumnState(base, saved)
        } else {
            root.activityColumns = base
        }
    }

    function _baseColumns() {
        return [
            { "key": "activityCode",      "label": "Activity ID", "flex": 0,   "minWidth": 96,  "sortable": true, "required": true, "visibleByDefault": true  },
            { "key": "wbs",               "label": "WBS",         "flex": 0,   "minWidth": 72,  "sortable": true, "visibleByDefault": true  },
            { "key": "taskName",          "label": "Task Name",   "flex": 2.1, "sortable": true, "required": true, "visibleByDefault": true  },
            { "key": "start",             "label": "Start",       "flex": 0,   "minWidth": 90,  "visibleByDefault": true  },
            { "key": "finish",            "label": "Finish",      "flex": 0,   "minWidth": 90,  "visibleByDefault": true  },
            { "key": "duration",          "label": "Duration",    "flex": 0,   "minWidth": 88,  "visibleByDefault": true  },
            { "key": "remainingDuration", "label": "Remaining",   "flex": 0,   "minWidth": 100, "visibleByDefault": true  },
            { "key": "float",             "label": "Float",       "flex": 0,   "minWidth": 72,  "visibleByDefault": true  },
            { "key": "critical",          "label": "Critical",    "flex": 0,   "minWidth": 88,  "type": "status",  "visibleByDefault": true  },
            { "key": "constraint",        "label": "Constraint",  "flex": 1.1, "visibleByDefault": false },
            { "key": "calendar",          "label": "Calendar",    "flex": 0.9, "visibleByDefault": false },
            { "key": "progress",          "label": "Progress",    "flex": 1.0, "minWidth": 120, "type": "progress", "visibleByDefault": true },
            { "key": "status",            "label": "Status",      "flex": 0.9, "type": "status", "visibleByDefault": true }
        ]
    }

    function _applyColumnState(base, saved) {
        const order = saved ? (saved.columnOrder || []) : []
        const hidden = saved ? (saved.hiddenColumns || []) : []
        if (order.length === 0) return base.slice()
        const hiddenSet = {}
        for (let i = 0; i < hidden.length; i++) hiddenSet[hidden[i]] = true
        const byKey = {}
        for (let i = 0; i < base.length; i++) byKey[base[i].key] = base[i]
        const result = []
        for (let j = 0; j < order.length; j++) {
            const col = byKey[order[j]]
            if (!col) continue
            const c = Object.assign({}, col)
            if (c.required !== true) c.visible = !hiddenSet[order[j]]
            result.push(c)
        }
        for (let i = 0; i < base.length; i++) {
            if (order.indexOf(base[i].key) < 0) result.push(Object.assign({}, base[i]))
        }
        return result
    }

    onActivePanelIdChanged: {
        if (root.workspaceController !== null)
            root.workspaceController.setActivePanel(root.activePanelId)
    }

    onWorkspaceControllerChanged: {
        if (root.workspaceController !== null)
            root.workspaceController.setActivePanel(root.activePanelId)
    }

    Component.onCompleted: initColumns()
}
