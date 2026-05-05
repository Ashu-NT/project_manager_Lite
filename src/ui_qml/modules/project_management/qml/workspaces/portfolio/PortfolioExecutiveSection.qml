import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Rectangle {
    id: root

    property var heatmapModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property var recentActionsModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.heatmapModel.title || "Portfolio Heatmap"
            subtitle: root.heatmapModel.subtitle || ""
            emptyState: root.heatmapModel.emptyState || ""
            items: root.heatmapModel.items || []
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.recentActionsModel.title || "Recent Actions"
            subtitle: root.recentActionsModel.subtitle || ""
            emptyState: root.recentActionsModel.emptyState || ""
            items: root.recentActionsModel.items || []
        }
    }
}
