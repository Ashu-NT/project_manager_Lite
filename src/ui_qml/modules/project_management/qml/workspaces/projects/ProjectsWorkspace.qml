import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppLayouts.WorkspaceFrame {
    property var workspaceModel: pmWorkspaceCatalog.workspace("project_management.projects")

    title: workspaceModel.title
    subtitle: workspaceModel.summary

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.MetricCard {
            Layout.preferredWidth: 260
            label: "Migration target"
            value: workspaceModel.migrationStatus
            supportingText: workspaceModel.legacyRuntimeStatus
        }
    }
}
