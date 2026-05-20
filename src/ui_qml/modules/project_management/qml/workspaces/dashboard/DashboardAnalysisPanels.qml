pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController

    readonly property var overviewModel: root.workspaceController ? (root.workspaceController.overview || {}) : ({})
    readonly property var panelModels: root.workspaceController ? (root.workspaceController.panels || []) : []
    readonly property var chartModels: root.workspaceController ? (root.workspaceController.charts || []) : []
    readonly property var healthPanel: root.panelModels.length > 0 ? root.panelModels[0] : ({ "rows": [], "metrics": [], "hint": "", "emptyState": "No schedule or cost health data is available yet." })
    readonly property var summaryPanel: root.panelModels.length > 1 ? root.panelModels[1] : ({ "rows": [], "metrics": [], "hint": "", "emptyState": "No risk summary is available yet." })
    readonly property var costPanel: root.panelModels.length > 2 ? root.panelModels[2] : ({ "rows": [], "metrics": [], "hint": "", "emptyState": "No cost-source summary is available yet." })
    readonly property var primaryChart: root.chartModels.length > 0 ? root.chartModels[0] : ({ "chartType": "line", "points": [], "emptyState": "No schedule trend is available yet." })
    readonly property bool showEmbeddedPrimaryChart: root.chartModels.length > 1
    readonly property int analysisColumns: width >= 1040 ? 2 : 1

    function limitEntries(entries, maxCount) {
        const values = []
        const source = entries || []
        for (let index = 0; index < source.length && index < maxCount; index += 1) {
            values.push(source[index])
        }
        return values
    }

    function progressMetrics() {
        const priorities = ["Progress", "In flight", "Blocked", "Late"]
        const source = root.overviewModel.metrics || []
        const selected = []
        for (let priorityIndex = 0; priorityIndex < priorities.length; priorityIndex += 1) {
            const label = priorities[priorityIndex]
            for (let metricIndex = 0; metricIndex < source.length; metricIndex += 1) {
                const metric = source[metricIndex] || {}
                if (String(metric.label || "") === label) {
                    selected.push(metric)
                    break
                }
            }
        }
        if (selected.length > 0) {
            return selected
        }
        return root.limitEntries(source, 4)
    }

    function summaryRows() {
        const merged = []
        const sourceRows = root.summaryPanel.rows || []
        for (let index = 0; index < sourceRows.length; index += 1) {
            merged.push(sourceRows[index])
        }
        const costRows = root.costPanel.rows || []
        for (let costIndex = 0; costIndex < costRows.length && costIndex < 2; costIndex += 1) {
            merged.push(costRows[costIndex])
        }
        return merged
    }

    implicitHeight: analysisGrid.implicitHeight

    GridLayout {
        id: analysisGrid

        anchors.fill: parent
        columns: root.analysisColumns
        columnSpacing: Theme.AppTheme.spacingSm
        rowSpacing: Theme.AppTheme.spacingSm

        DashboardPanelFrame {
            Layout.fillWidth: true
            Layout.preferredHeight: root.analysisColumns === 2 ? 300 : 360
            title: "Schedule / Cost Health"
            subtitle: root.showEmbeddedPrimaryChart
                ? (root.primaryChart.subtitle || root.healthPanel.subtitle || "")
                : (root.healthPanel.subtitle || "")

            ProjectManagementWidgets.DashboardChartCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 144
                visible: root.showEmbeddedPrimaryChart
                title: ""
                subtitle: ""
                chartType: root.primaryChart.chartType || "line"
                emptyState: root.primaryChart.emptyState || ""
                points: root.primaryChart.points || []
            }

            DashboardInsightPanel {
                Layout.fillWidth: true
                hint: root.healthPanel.hint || ""
                emptyState: root.healthPanel.emptyState || ""
                rows: root.healthPanel.rows || []
                metrics: root.showEmbeddedPrimaryChart
                    ? root.limitEntries(root.healthPanel.metrics || [], 2)
                    : root.limitEntries(root.healthPanel.metrics || [], 4)
            }
        }

        DashboardPanelFrame {
            Layout.fillWidth: true
            Layout.preferredHeight: root.analysisColumns === 2 ? 300 : 320
            title: "Risk / Progress Summary"
            subtitle: root.summaryPanel.subtitle || "Execution pressure, overdue items, and current project momentum."

            DashboardInsightPanel {
                Layout.fillWidth: true
                hint: root.summaryPanel.hint || root.costPanel.hint || ""
                emptyState: root.summaryPanel.emptyState || ""
                metrics: root.progressMetrics()
                rows: root.summaryRows()
            }
        }
    }
}
