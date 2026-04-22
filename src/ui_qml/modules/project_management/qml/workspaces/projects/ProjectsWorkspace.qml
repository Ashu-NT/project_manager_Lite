import QtQuick
import QtQuick.Layouts
import "../../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../../shared/qml/theme" as Theme
import "../../../../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    property var workspaceModel: pmWorkspaceCatalog.workspace("project_management.projects")

    title: workspaceModel.title
    subtitle: workspaceModel.summary

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Widgets.MetricCard {
            Layout.preferredWidth: 260
            label: "Migration target"
            value: workspaceModel.migrationStatus
            supportingText: workspaceModel.legacyRuntimeStatus
        }
    }
}
