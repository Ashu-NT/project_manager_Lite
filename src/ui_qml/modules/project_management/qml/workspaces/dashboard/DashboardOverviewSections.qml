pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Flow {
    id: root

    property ProjectManagementControllers.ProjectManagementDashboardWorkspaceController workspaceController
    property string emptyState: ""

    width: parent ? parent.width : implicitWidth
    spacing: Theme.AppTheme.spacingMd

    Label {
        width: root.width
        visible: root.emptyState.length > 0
        text: root.emptyState
        color: Theme.AppTheme.textSecondary
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.smallSize
        wrapMode: Text.WordWrap
    }

    Repeater {
        model: root.workspaceController ? (root.workspaceController.sections || []) : []

        delegate: ProjectManagementWidgets.DashboardSectionCard {
            required property var modelData

            width: root.width >= 960
                ? Math.max(320, (root.width - root.spacing) / 2)
                : root.width
            title: modelData.title || ""
            subtitle: modelData.subtitle || ""
            emptyState: modelData.emptyState || ""
            items: modelData.items || []
        }
    }
}
