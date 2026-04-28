import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppLayouts.WorkspaceFrame {
    id: root
    property var pmCatalog: null
    property var workspaceModel: root.pmCatalog
        ? root.pmCatalog.workspace("project_management.resources")
        : ({
            "title": "Resources",
            "summary": "",
            "migrationStatus": "Placeholder",
            "legacyRuntimeStatus": "Legacy QWidget resources workspace remains active."
        })

    title: root.workspaceModel.title
    subtitle: root.workspaceModel.summary

    RowLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.MetricCard {
            Layout.preferredWidth: 260
            label: "Migration target"
            value: root.workspaceModel.migrationStatus
            supportingText: root.workspaceModel.legacyRuntimeStatus
        }
    }
}
