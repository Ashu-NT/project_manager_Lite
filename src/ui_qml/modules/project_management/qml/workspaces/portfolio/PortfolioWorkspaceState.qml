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
    readonly property var topAtRiskModel: root.workspaceController
        ? root.workspaceController.topAtRiskProjects
        : ({ "title": "Top At-Risk Projects", "subtitle": "", "emptyState": "", "items": [] })

    // ── Primary tab bar (R3.4 six-tab IA) ──────────────────────────────────
    readonly property var tabKeys: ["executive", "heatmap", "intake", "scenarios", "capacity", "dependencies"]
    readonly property var tabLabels: ["Executive", "Heatmap", "Intake", "Scenarios", "Capacity", "Dependencies"]
    readonly property int activeTabIndex: {
        const key = root.workspaceController ? root.workspaceController.activeTab : "executive"
        const idx = root.tabKeys.indexOf(key)
        return idx >= 0 ? idx : 0
    }

    // ── Mutable UI state ──────────────────────────────────────────────────
    property string selectedRowId:        ""
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

}
