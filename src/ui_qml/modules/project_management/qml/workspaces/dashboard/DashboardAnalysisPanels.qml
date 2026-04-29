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
        model: root.workspaceController ? (root.workspaceController.panels || []) : []

        delegate: ProjectManagementWidgets.DashboardPanelCard {
            required property var modelData

            width: root.width >= 1320
                ? Math.max(320, (root.width - (Theme.AppTheme.spacingMd * 2)) / 3)
                : root.width >= 860
                    ? Math.max(320, (root.width - Theme.AppTheme.spacingMd) / 2)
                    : root.width
            title: modelData.title || ""
            subtitle: modelData.subtitle || ""
            hint: modelData.hint || ""
            emptyState: modelData.emptyState || ""
            rows: modelData.rows || []
            metrics: modelData.metrics || []
        }
    }
}
