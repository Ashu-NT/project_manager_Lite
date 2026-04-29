pragma ComponentBehavior: Bound
import QtQuick
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Flow {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController

    width: parent ? parent.width : implicitWidth
    spacing: Theme.AppTheme.spacingMd

    Repeater {
        model: root.workspaceController ? (root.workspaceController.charts || []) : []

        delegate: ProjectManagementWidgets.DashboardChartCard {
            required property var modelData

            width: root.width >= 960
                ? Math.max(360, (root.width - Theme.AppTheme.spacingMd) / 2)
                : root.width
            title: modelData.title || ""
            subtitle: modelData.subtitle || ""
            chartType: modelData.chartType || "bar"
            emptyState: modelData.emptyState || ""
            points: modelData.points || []
        }
    }
}
