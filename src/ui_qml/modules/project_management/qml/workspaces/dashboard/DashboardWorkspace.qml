import QtQuick
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property var pmCatalog: null
    property var workspaceModel: root.pmCatalog
        ? root.pmCatalog.workspace("project_management.dashboard")
        : ({
            "routeId": "project_management.dashboard",
            "title": "Dashboard",
            "summary": "",
            "migrationStatus": "Placeholder",
            "legacyRuntimeStatus": "Legacy QWidget dashboard remains active."
        })
    property var dashboardOverview: root.pmCatalog
        ? root.pmCatalog.dashboardOverview()
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    title: root.dashboardOverview.title
    subtitle: root.dashboardOverview.subtitle

    Flow {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Repeater {
            model: root.dashboardOverview.metrics

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
