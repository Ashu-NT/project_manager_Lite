pragma ComponentBehavior: Bound
import QtQuick
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    // ── Injected ──────────────────────────────────────────────────────────
    property ProjectManagementControllers.ProjectManagementPortfolioWorkspaceController workspaceController

    // ── Raw models (controller fallbacks keep UI live in preview) ─────────
    readonly property var heatmapModel: root.workspaceController
        ? root.workspaceController.heatmap
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var intakeModel: root.workspaceController
        ? root.workspaceController.intakeItems
        : ({ "title": "", "subtitle": "", "emptyState": "No intake items.", "items": [] })
    readonly property var dependenciesModel: root.workspaceController
        ? root.workspaceController.dependencies
        : ({ "title": "", "subtitle": "", "emptyState": "No dependencies.", "items": [] })
    readonly property var scenariosModel: root.workspaceController
        ? root.workspaceController.scenarios
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var templatesModel: root.workspaceController
        ? root.workspaceController.templates
        : ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    readonly property var recentActionsModel: root.workspaceController
        ? root.workspaceController.recentActions
        : ({ "title": "", "subtitle": "", "emptyState": "No recent activity.", "items": [] })
    readonly property var capacityPoolModel: root.workspaceController
        ? root.workspaceController.capacityPool
        : ({ "title": "Capacity Pool", "subtitle": "", "emptyState": "No capacity data available.", "items": [] })

    // ── Mutable UI state ──────────────────────────────────────────────────
    property string selectedRowId:        ""
    property var    selectedRowIds:       []
    property int    bottomTab:            0
    property string selectedFundingId:    ""
    property bool   detailOpen:           false
    property int    pendingDetailSection: 0

    // ── Column definitions ────────────────────────────────────────────────
    readonly property var heatmapColumns: [
        { "key": "title",          "label": "Project",       "flex": 3, "minWidth": 180, "sortable": true },
        { "key": "subtitle",       "label": "Status",        "flex": 1, "minWidth": 90                    },
        { "key": "statusLabel",    "label": "Pressure",      "flex": 1, "minWidth": 80, "type": "status"  },
        { "key": "supportingText", "label": "Delivery",      "flex": 2, "minWidth": 160                   },
        { "key": "metaText",       "label": "Cost Variance", "flex": 1, "minWidth": 100                   }
    ]

    readonly property var fundingColumns: [
        { "key": "title",          "label": "Intake Item",       "flex": 3, "minWidth": 160, "sortable": true },
        { "key": "statusLabel",    "label": "Status",            "flex": 1, "minWidth": 90,  "type": "status" },
        { "key": "subtitle",       "label": "Sponsor",           "flex": 2, "minWidth": 120                   },
        { "key": "supportingText", "label": "Budget / Capacity", "flex": 2, "minWidth": 160                   },
        { "key": "metaText",       "label": "Score",             "flex": 1, "minWidth": 60                    }
    ]

    readonly property var riskColumns: [
        { "key": "title",          "label": "Dependency", "flex": 3, "minWidth": 200                  },
        { "key": "subtitle",       "label": "Type",       "flex": 1, "minWidth": 100                  },
        { "key": "statusLabel",    "label": "Pressure",   "flex": 1, "minWidth": 80, "type": "status" },
        { "key": "supportingText", "label": "Status",     "flex": 2, "minWidth": 160                  }
    ]

    // ── Computed rows ─────────────────────────────────────────────────────
    readonly property var selectedHeatmapItem: {
        const id = root.selectedRowId
        if (!id) return null
        const items = root.heatmapModel.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id || "") === id) return items[i]
        }
        return null
    }

    readonly property var activityItems: {
        return (root.recentActionsModel.items || []).map(function(item) {
            return {
                "title":       String(item.title       || ""),
                "metaText":    String(item.metaText    || item.subtitle || ""),
                "statusLabel": String(item.statusLabel || "")
            }
        })
    }

    // ── Helpers ───────────────────────────────────────────────────────────
    function optionIndexForValue(options, value) {
        const opts = options || []
        for (let i = 0; i < opts.length; i += 1) {
            if (String(opts[i].value || "") === String(value || "")) return i
        }
        return 0
    }
}
