import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppLayouts.WorkspaceFrame {
    property var workspaceModel: pmWorkspaceCatalog.workspace("project_management.dashboard")
    property var dashboardOverview: pmWorkspaceCatalog.dashboardOverview()

    title: dashboardOverview.title
    subtitle: dashboardOverview.subtitle

    Flow {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Repeater {
            model: dashboardOverview.metrics

            delegate: AppWidgets.MetricCard {
                required property var modelData

                width: 230
                label: modelData.label
                value: modelData.value
                supportingText: modelData.supportingText
            }
        }
    }
}
