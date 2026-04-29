import QtQuick
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Flow {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController
    property var workspaceModel: ({})

    spacing: Theme.AppTheme.spacingMd

    AppWidgets.MetricCard {
        width: 280
        label: "Render layer"
        value: "QML workspace page"
        supportingText: "The page binds typed controller state and keeps orchestration out of the QML layer."
    }

    AppWidgets.MetricCard {
        width: 280
        label: "Empty state"
        value: root.workspaceController ? root.workspaceController.emptyState : "Select a project"
        supportingText: root.workspaceModel.legacyRuntimeStatus || ""
    }
}
