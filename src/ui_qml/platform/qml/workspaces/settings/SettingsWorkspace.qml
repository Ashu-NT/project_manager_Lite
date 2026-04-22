import QtQuick
import QtQuick.Layouts
import "../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../shared/qml/theme" as Theme
import "../../../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    property var workspaceModel: platformWorkspaceCatalog.workspace("platform.settings")
    property var runtimeOverview: platformWorkspaceCatalog.runtimeOverview()

    title: workspaceModel.title
    subtitle: "Shell preferences and runtime settings through QML-safe platform state."

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Widgets.MetricCard {
            Layout.preferredWidth: 240
            label: "Platform API"
            value: runtimeOverview.statusLabel
            supportingText: workspaceModel.summary
        }

        Widgets.MetricCard {
            Layout.preferredWidth: 240
            label: "Theme"
            value: shellContext.themeMode
            supportingText: "Theme state is exposed through shellContext for QML binding."
        }
    }
}
