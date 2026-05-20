pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController

    readonly property var chartModels: root.workspaceController ? (root.workspaceController.charts || []) : []
    readonly property var visibleCharts: root.chartModels.length > 1
        ? root.chartModels.slice(1)
        : root.chartModels
    readonly property int chartColumns: width >= 1040 && root.visibleCharts.length > 1 ? 2 : 1

    implicitHeight: root.visibleCharts.length > 0 ? chartsGrid.implicitHeight : 0
    visible: root.visibleCharts.length > 0

    GridLayout {
        id: chartsGrid

        anchors.fill: parent
        columns: root.chartColumns
        columnSpacing: Theme.AppTheme.spacingSm
        rowSpacing: Theme.AppTheme.spacingSm

        Repeater {
            model: root.visibleCharts

            delegate: DashboardPanelFrame {
                id: chartFrame
                required property var modelData

                Layout.fillWidth: true
                Layout.preferredHeight: root.chartColumns === 2 ? 236 : 248
                title: chartFrame.modelData.title || ""
                subtitle: chartFrame.modelData.subtitle || ""

                ProjectManagementWidgets.DashboardChartCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: ""
                    subtitle: ""
                    chartType: chartFrame.modelData.chartType || "bar"
                    emptyState: chartFrame.modelData.emptyState || ""
                    points: chartFrame.modelData.points || []
                }
            }
        }
    }
}
