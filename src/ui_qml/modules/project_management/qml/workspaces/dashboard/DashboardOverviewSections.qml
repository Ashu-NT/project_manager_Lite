pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController
    property string emptyState: ""

    readonly property var sectionModels: root.workspaceController ? (root.workspaceController.sections || []) : []
    readonly property var panelModels: root.workspaceController ? (root.workspaceController.panels || []) : []
    readonly property var overviewModel: root.workspaceController ? (root.workspaceController.overview || {}) : ({})
    readonly property var milestoneSection: root.matchingSection(["Milestones", "Portfolio Ranking"])
    readonly property var issuesSection: root.matchingSection(["Urgent Register Items", "Alerts"])
    readonly property var taskSection: root.matchingSection(["Critical Path", "Upcoming Work"])
    readonly property var costPanel: root.panelModels.length > 2 ? root.panelModels[2] : ({ "rows": [] })

    function matchingSection(preferredTitles) {
        const sections = root.sectionModels || []
        const titles = preferredTitles || []
        for (let titleIndex = 0; titleIndex < titles.length; titleIndex += 1) {
            const needle = String(titles[titleIndex] || "").toLowerCase()
            for (let sectionIndex = 0; sectionIndex < sections.length; sectionIndex += 1) {
                const section = sections[sectionIndex] || {}
                if (String(section.title || "").toLowerCase().indexOf(needle) !== -1) {
                    return section
                }
            }
        }
        return sections.length > 0 ? sections[0] : ({ "title": "", "subtitle": "", "items": [], "emptyState": root.emptyState })
    }

    function sectionColumns(primaryLabel, secondaryLabel, tertiaryLabel) {
        return [
            { "key": "title", "label": primaryLabel, "flex": 3, "minWidth": 180, "sortable": true, "visible": true },
            { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 96, "sortable": false, "visible": true, "type": "status" },
            { "key": "subtitle", "label": secondaryLabel, "flex": 2, "minWidth": 160, "sortable": false, "visible": true },
            { "key": "supportingText", "label": tertiaryLabel, "flex": 2, "minWidth": 160, "sortable": false, "visible": true },
            { "key": "metaText", "label": "Summary", "flex": 2, "minWidth": 160, "sortable": false, "visible": true }
        ]
    }

    function sectionRows(sectionModel) {
        const rows = []
        const items = sectionModel && sectionModel.items ? sectionModel.items : []
        for (let index = 0; index < items.length; index += 1) {
            const item = items[index] || {}
            rows.push({
                "id": String(item.id || ("row-" + index)),
                "title": item.title || "",
                "statusLabel": item.statusLabel || "",
                "subtitle": item.subtitle || "",
                "supportingText": item.supportingText || "",
                "metaText": item.metaText || ""
            })
        }
        return rows
    }

    function budgetColumns() {
        return [
            { "key": "source", "label": "Budget Line", "flex": 2, "minWidth": 150, "sortable": true, "visible": true },
            { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 92, "sortable": false, "visible": true, "type": "status" },
            { "key": "value", "label": "Spend vs Plan", "flex": 2, "minWidth": 150, "sortable": false, "visible": true },
            { "key": "supportingText", "label": "Committed", "flex": 2, "minWidth": 140, "sortable": false, "visible": true }
        ]
    }

    function budgetRows() {
        const rows = []
        const sourceRows = root.costPanel && root.costPanel.rows ? root.costPanel.rows : []
        for (let index = 0; index < sourceRows.length; index += 1) {
            const row = sourceRows[index] || {}
            let statusLabel = ""
            if (String(row.tone || "") === "danger") {
                statusLabel = "Attention"
            } else if (String(row.tone || "") === "warning") {
                statusLabel = "Watch"
            } else if (String(row.tone || "") === "success") {
                statusLabel = "Healthy"
            }
            rows.push({
                "id": "budget-" + index,
                "source": row.label || "",
                "statusLabel": statusLabel,
                "value": row.value || "",
                "supportingText": row.supportingText || ""
            })
        }
        return rows
    }

    implicitHeight: dashboardLayout.implicitHeight

    ColumnLayout {
        id: dashboardLayout

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        DashboardTablePanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 258
            title: root.milestoneSection.title || "Delivery Overview"
            subtitle: root.milestoneSection.subtitle || "Milestone health and delivery checkpoints."
            columns: root.sectionColumns("Milestone", "Owner / Context", "Target / Due")
            rows: root.sectionRows(root.milestoneSection)
            loading: root.workspaceController ? root.workspaceController.isLoading : false
            emptyText: root.milestoneSection.emptyState || root.emptyState || "No milestone or delivery rows are available yet."
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: width >= 1380 ? 3 : width >= 960 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingSm
            rowSpacing: Theme.AppTheme.spacingSm

            DashboardTablePanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: 250
                title: root.issuesSection.title || "Recent Issues"
                subtitle: root.issuesSection.subtitle || "Open issues, alerts, and urgent register entries."
                columns: root.sectionColumns("Issue", "Context", "Due / Owner")
                rows: root.sectionRows(root.issuesSection)
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.issuesSection.emptyState || "No recent issues are active."
            }

            DashboardTablePanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: 250
                title: root.taskSection.title || "Delayed Tasks"
                subtitle: root.taskSection.subtitle || "Critical path and upcoming execution pressure."
                columns: root.sectionColumns("Task", "Schedule", "Owner / Progress")
                rows: root.sectionRows(root.taskSection)
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.taskSection.emptyState || "No delayed or critical tasks are active."
            }

            DashboardTablePanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: 250
                title: "Budget Lines"
                subtitle: "Committed spend versus current planning lines."
                columns: root.budgetColumns()
                rows: root.budgetRows()
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: "No budget-line rows are available yet."
            }
        }
    }
}
