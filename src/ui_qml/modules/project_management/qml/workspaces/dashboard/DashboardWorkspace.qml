import QtQuick
import QtQuick.Layouts
import "../../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../../shared/qml/theme" as Theme
import "../../../../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    property var workspaceModel: pmWorkspaceCatalog.workspace("project_management.dashboard")
    property var dashboardOverview: pmWorkspaceCatalog.dashboardOverview()

    title: dashboardOverview.title
    subtitle: dashboardOverview.subtitle

    Flow {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Repeater {
            model: dashboardOverview.metrics

            delegate: Widgets.MetricCard {
                required property var modelData

                width: 230
                label: modelData.label
                value: modelData.value
                supportingText: modelData.supportingText
            }
        }
    }
}
