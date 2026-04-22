import QtQuick
import QtQuick.Layouts
import "../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../shared/qml/theme" as Theme
import "../../../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    property var workspaceModel: platformWorkspaceCatalog.workspace("platform.admin")
    property var runtimeOverview: platformWorkspaceCatalog.runtimeOverview()

    title: workspaceModel.title
    subtitle: runtimeOverview.subtitle

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Widgets.MetricCard {
            Layout.preferredWidth: 240
            label: "Platform API"
            value: runtimeOverview.statusLabel
            supportingText: workspaceModel.summary
        }

        Repeater {
            model: runtimeOverview.metrics

            delegate: Widgets.MetricCard {
                required property var modelData

                Layout.preferredWidth: 240
                label: modelData.label
                value: modelData.value
                supportingText: modelData.supportingText
            }
        }
    }
}
